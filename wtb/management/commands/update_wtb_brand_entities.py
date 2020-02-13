from django.core.management import BaseCommand
from wtb.models import WtbBrand


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--brand', type=int)

    def handle(self, *args, **options):
        brand = WtbBrand.objects.get(pk=options['brand'])
        brand.update_entities()
