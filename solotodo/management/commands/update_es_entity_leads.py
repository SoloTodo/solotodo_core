from datetime import timedelta

from django.core.management import BaseCommand
from django.db.models import Count
from django.utils import timezone

from solotodo.models import Lead, EsEntity


class Command(BaseCommand):
    def handle(self, *args, **options):
        leads = (
            Lead.objects.filter(timestamp__gte=timezone.now() - timedelta(days=14))
            .order_by("entity_history__entity")
            .values("entity_history__entity")
            .annotate(c=Count("*"))
        )
        leads_dict = {x["entity_history__entity"]: x["c"] for x in leads}
        es_results = EsEntity.search()
        result_count = es_results.count()

        for idx, es_hit in enumerate(es_results.scan()):
            print("{} / {}".format(idx + 1, result_count))
            leads = leads_dict.get(es_hit.entity_id, 0)
            es_entity = EsEntity(**es_hit.to_dict(), meta=es_hit.meta.to_dict())
            es_entity.leads = leads
            es_entity.save()
