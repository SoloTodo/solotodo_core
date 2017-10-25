from django.core.management import BaseCommand

from solotodo.models import Store
from solotodo.tasks import store_update


class Command(BaseCommand):
    def handle(self, *args, **options):
        stores = Store.objects.filter(is_active=True)

        for store in stores:
            try:
                store.scraper
                store_update.delay(store.id)
            except AttributeError:
                pass
