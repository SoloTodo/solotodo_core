from datetime import datetime

import pytz
from django.core.management import BaseCommand

from solotodo.models import Store


class Command(BaseCommand):
    def handle(self, *args, **options):
        Store.objects.update(
            last_activation=pytz.utc.localize(datetime(2018, 1, 1)))
