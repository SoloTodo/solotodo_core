from django.core.management import BaseCommand

from lg_pricing.models import LgRsEntityHistory


class Command(BaseCommand):
    def handle(self, *args, **options):
        LgRsEntityHistory.synchronize_with_db_entity_histories()
