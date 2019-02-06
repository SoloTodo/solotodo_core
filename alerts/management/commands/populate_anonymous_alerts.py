from django.core.management import BaseCommand

from alerts.models import Alert
from alerts.models import AnonymousAlert


class Command(BaseCommand):
    def handle(self, *args, **options):
        alerts = Alert.objects.all()
        q = len(alerts)
        for i, alert in enumerate(alerts):
            print('{} de {} - {}'.format(i, q, alert.id))
            AnonymousAlert.objects.create(email=alert.email, alert=alert)
