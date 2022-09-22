import urllib

from django.utils import timezone
from django.core.management import BaseCommand

from solotodo.models import SoloTodoUser
from reports.tasks import send_weekly_prices_task


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--user_ids', nargs='+', type=int)

    def handle(self, *args, **options):
        user_ids = options['user_ids']

        users = SoloTodoUser.objects.filter(pk__in=user_ids)

        # Determine date from/to
        date_to = timezone.now()
        date_from = timezone.datetime(2021, 1, 1)

        request = 'timestamp_after={}&timestamp_before={}&category=4'.format(
            urllib.parse.quote(date_from.isoformat()),
            urllib.parse.quote(date_to.isoformat())
        )

        send_weekly_prices_task.delay(users[0].id, request)
