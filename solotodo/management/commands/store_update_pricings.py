from django.core.management import BaseCommand

from solotodo.models import Store
from solotodo.tasks import store_update


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--stores', nargs='*', type=str)

    def handle(self, *args, **options):
        store_names = options['stores']
        stores = Store.objects.filter(is_active=True)

        if store_names:
            stores = stores.filter(name__in=store_names)

        for store in stores:
            try:
                store.scraper
                store_update.delay(store.id)
            except AttributeError:
                pass
