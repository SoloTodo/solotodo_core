import json

from django.core.management import BaseCommand
from wtb.models import WtbBrand


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--brand", type=int)
        parser.add_argument(
            "--extra_args",
            type=json.loads,
            nargs="?",
            default={},
            help="Optional arguments to pass to the parser "
            "(usually username/password) for private sites)",
        )

    def handle(self, *args, **options):
        extra_args = options["extra_args"]
        brand = WtbBrand.objects.get(pk=options["brand"])
        brand.update_entities(extra_args=extra_args)
