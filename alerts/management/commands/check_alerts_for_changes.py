from django.core.management import BaseCommand

from alerts.models.alert import Alert
from alerts.tasks import alert_check_for_changes


class Command(BaseCommand):
    def handle(self, *args, **options):
        for alert in Alert.objects.all():
            alert_check_for_changes.delay(alert.id)
