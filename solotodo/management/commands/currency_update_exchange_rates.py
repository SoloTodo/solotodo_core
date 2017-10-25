from django.core.management import BaseCommand

from solotodo.models import Currency


class Command(BaseCommand):
    def handle(self, *args, **options):
        for currency in Currency.objects.all():
            currency.update_exchange_rate()
