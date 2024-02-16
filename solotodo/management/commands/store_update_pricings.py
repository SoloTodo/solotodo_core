import json

from django.core.management import BaseCommand

from solotodo.models import Store
from solotodo.tasks import store_update


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--stores", nargs="*", type=str)
        parser.add_argument(
            "--extra_args",
            type=json.loads,
            nargs="?",
            default={},
            help="Optional arguments to pass to the parser "
            "(usually username/password) for private sites)",
        )

    def handle(self, *args, **options):
        store_names = options["stores"]
        extra_args = options["extra_args"]
        stores = Store.objects.filter(last_activation__isnull=False)

        if store_names:
            stores = stores.filter(name__in=store_names)

        for store in stores:
            try:
                store.scraper
                store_update.delay(store.id, extra_args=extra_args)
            except AttributeError:
                pass
