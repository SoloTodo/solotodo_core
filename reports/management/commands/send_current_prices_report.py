from django.core.management import BaseCommand
from reports.tasks import send_current_prices_task


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--user_ids', nargs='+', type=int)
        parser.add_argument('--category_id', type=int)

    def handle(self, *args, **options):
        user_ids = options['user_ids']
        send_current_prices_task(user_ids, 'category={}'.format(options['category_id']))
