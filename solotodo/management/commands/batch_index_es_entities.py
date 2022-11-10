from datetime import timedelta
from itertools import repeat
from multiprocessing import cpu_count, Pool

from django.core.management import BaseCommand
from django.db import models
from django.db.models import Avg, Min, Count

from solotodo.models import Entity, EntityHistory, EsEntity, Lead


class Epoch(models.expressions.Func):
    template = 'EXTRACT(epoch FROM %(expressions)s)::FLOAT'
    output_field = models.FloatField()


class DateTimeFromFloat(models.expressions.Func):
    template = 'To_TIMESTAMP(%(expressions)s)::TIMESTAMP at time zone \'UTC\''
    output_field = models.DateTimeField()


def index_entity(entity, prices_dict, leads_dict, idx):
    # Top level function used by multiprocessing
    print('Entity {} ({})'.format(idx, entity.id))
    EsEntity.from_entity(entity, prices_dict, leads_dict).save()


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
            'category',
            'best_coupon'
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

        print('Before indexing, it is a good idea to limit '
              'ElasticSearch RAM usage to 8 GB or so by creating a '
              'config/jvm.options.d/memory.options with the flags -Xms8g '
              'and -Xmx8g')
        print('{} entities will be indexed'.format(len(es)))
        print('Your computer has {} available cores'.format(cpu_count()))
        core_target = int(input('How many cores do you want to use for '
                                'indexing? (ideally leave 4 or so for '
                                'Elasticsearch and other stuff) '))
        print('Creating pool with {} workers'.format(core_target))
        pool = Pool(processes=core_target)
        pool.starmap(index_entity, zip(
            es, repeat(prices_dict), repeat(leads_dict), range(len(es))))
        pool.close()
        pool.join()
