from django.core.management import BaseCommand

from solotodo.models import EsProductEntities


class Command(BaseCommand):
    def handle(self, *args, **options):
        EsProductEntities.init()
