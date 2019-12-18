from django.core.management import BaseCommand

from brand_comparisons.models import BrandComparisonAlert
from brand_comparisons.tasks import alert_check_for_changes


class Command(BaseCommand):
    def handle(self, *args, **options):
        for alert in BrandComparisonAlert.objects.all():
            alert_check_for_changes.delay(alert.id)
