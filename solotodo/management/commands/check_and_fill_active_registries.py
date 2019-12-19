from django.core.management import BaseCommand
from solotodo.models import Store


class Command(BaseCommand):
    def handle(self, *args, **options):
        stores = Store.objects.get(last_activation__isnull=False)

        for store in stores:
            store.check_and_fill_active_registries()
