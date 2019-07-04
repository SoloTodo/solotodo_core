from django.core.management import BaseCommand

from lg_pricing.models import LgRsBanner


class Command(BaseCommand):
    def handle(self, *args, **options):
        LgRsBanner.synchronize_with_db_banners()
