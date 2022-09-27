from django.core.management import BaseCommand

from solotodo.models import Entity
from solotodo.tasks import entity_save


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
        )
        for e in es:
            entity_save.delay(e.id)
