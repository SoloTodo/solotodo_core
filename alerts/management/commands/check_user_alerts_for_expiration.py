from django.core.management import BaseCommand

from alerts.models import ProductPriceAlert
from alerts.tasks import alert_check_for_expiration


class Command(BaseCommand):
    def handle(self, *args, **options):
        for alert in ProductPriceAlert.objects.filter(user__isnull=False):
            alert_check_for_expiration.delay(alert.id)
