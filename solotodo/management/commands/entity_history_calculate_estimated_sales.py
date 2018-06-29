from django.conf import settings
from django.core.management import BaseCommand

from solotodo.models import EntityHistory


class Command(BaseCommand):
    def handle(self, *args, **options):
        ehs = EntityHistory.objects.exclude(stock=-1).order_by(
            'entity', 'timestamp').select_related('entity')

        last_eh_seen = None

        for idx, eh in enumerate(ehs.iterator()):
            print('Cycle: ', idx)
            if last_eh_seen and eh.entity_id == last_eh_seen.entity_id:
                estimated_sales = last_eh_seen.stock - eh.stock
                if estimated_sales > 0:
                    if eh.entity.store_id in settings.UNRELIABLE_STOCK_STORES \
                            and estimated_sales >= \
                            settings.UNRELIABLE_STOCK_STORE_SALES_THRESHOLD:
                        continue

                    eh.estimated_sales_since_previous_registry = \
                        estimated_sales
                    eh.save()
            last_eh_seen = eh
