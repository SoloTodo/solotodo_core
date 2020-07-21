from django.core.management import BaseCommand
from django.utils import timezone
from datetime import timedelta

from alerts.models import ProductPriceAlert
from alerts.tasks import alert_revoke


class Command(BaseCommand):
    def handle(self, *args, **options):
        date = timezone.now() - timedelta(days=30)
        expired_alerts = ProductPriceAlert.objects.filter(
            email__isnull=False,
            creation_date__lte=date)
        for alert in expired_alerts:
            alert_revoke.delay(alert.id)
