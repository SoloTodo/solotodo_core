from datetime import timedelta

from django.core.management import BaseCommand
from django.db import models
from django.db.models import Avg, Min, Count

from solotodo.models import Entity, EntityHistory, EsEntity, Lead
from solotodo.tasks import entity_save


class Epoch(models.expressions.Func):
    template = 'EXTRACT(epoch FROM %(expressions)s)::FLOAT'
    output_field = models.FloatField()


class DateTimeFromFloat(models.expressions.Func):
    template = 'To_TIMESTAMP(%(expressions)s)::TIMESTAMP at time zone \'UTC\''
    output_field = models.DateTimeField()


class Command(BaseCommand):
    def handle(self, *args, **options):
        # If you need to delete the previous indexed entities run the
        # following query from Kibana
        # POST /product_entities/_delete_by_query
        # {"query": {"bool": {"filter": [{"term":
        # {"product_relationships": "entity"}}]}}}

        es = Entity.objects.get_available().filter(
            product__isnull=False,
            active_registry__cell_monthly_payment__isnull=True
        ).select_related(
            'active_registry',
            'currency',
            'bundle',
            'product__brand',
            'store__country',
            'category'
        )

        # Ideally each entity should calculate its reference price and leads
        # with individual timestamps, but since "most" of them will have more
        # or less the same one (as prices update daily at the same hour) we
        # can use the average of them to have some good initial data and allow
        # batch processing.

        timestamp = es.aggregate(avg_timestamp=DateTimeFromFloat(
            Avg(Epoch('active_registry__timestamp'))))['avg_timestamp']

        reference_prices = EntityHistory.objects.filter(
            entity__in=es,
            timestamp__gte=timestamp - timedelta(hours=84),
            timestamp__lte=timestamp - timedelta(hours=36)
        ).order_by('entity').values('entity').annotate(
            min_normal_price=Min('normal_price'),
            min_offer_price=Min('offer_price')
        )

        prices_dict = {x['entity']: (x['min_normal_price'], x['min_offer_price']) for x in reference_prices}

        leads = Lead.objects.filter(
            entity_history__entity__in=es,
            timestamp__gte=timestamp - timedelta(hours=72)
        ).order_by('entity_history__entity')\
            .values('entity_history__entity')\
            .annotate(c=Count('*'))

        leads_dict = {x['entity_history__entity']: x['c'] for x in leads}

        es_count = es.count()

        for idx, e in enumerate(es):
            print('{} / {}: {}'.format(idx + 1, es_count, e.id))
            EsEntity.from_entity(e, prices_dict, leads_dict)
