from django.core.management import BaseCommand

from alerts.models import AnonymousAlert
from alerts.tasks import anonymous_alert_check_for_changes


class Command(BaseCommand):
    def handle(self, *args, **options):
        for alert in AnonymousAlert.objects.all():
            anonymous_alert_check_for_changes.delay(alert.id)
