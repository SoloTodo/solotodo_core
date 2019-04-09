from django.core.management import BaseCommand

from solotodo.models import Store
from banners.tasks import store_update_banners


class Command(BaseCommand):
    def handle(self, *args, **options):
        stores = Store.objects.all().filter_by_banners_support()

        for store in stores:
            store_update_banners.delay(store.id)
