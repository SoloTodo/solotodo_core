from django.core.management import BaseCommand
from django.db import connection


class Command(BaseCommand):
    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            cursor.execute(
                "REFRESH MATERIALIZED VIEW solotodo_materializedentity")
