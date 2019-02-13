from django.core.management import BaseCommand

from alerts.models import UserAlert
from alerts.tasks import user_alert_check_for_changes


class Command(BaseCommand):
    def handle(self, *args, **options):
        for alert in UserAlert.objects.all():
            user_alert_check_for_changes.delay(alert.id)
