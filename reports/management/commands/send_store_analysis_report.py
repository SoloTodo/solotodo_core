from django.core.management import BaseCommand
from reports.tasks import send_store_analysis_report_task


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--user_id', nargs=1, type=int)
        parser.add_argument('--query_string', nargs=1, type=str)

    def handle(self, *args, **options):
        user_id = options['user_id'][0]
        query_string = options['query_string'][0]
        send_store_analysis_report_task.delay(user_id, query_string)
