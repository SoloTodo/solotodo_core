from django.core.management import BaseCommand

from lg_pricing.models import LgRsEntitySectionPosition


class Command(BaseCommand):
    def handle(self, *args, **options):
        LgRsEntitySectionPosition.synchronize_with_db_positions()
