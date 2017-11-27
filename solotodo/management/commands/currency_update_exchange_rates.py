from django.core.management import BaseCommand

from solotodo.models import Currency


class Command(BaseCommand):
    def handle(self, *args, **options):
        Currency.update_exchange_rates()
