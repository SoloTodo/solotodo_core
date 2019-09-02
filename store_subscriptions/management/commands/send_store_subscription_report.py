from django.core.management import BaseCommand

from store_subscriptions.models import StoreSubscription
from store_subscriptions.tasks import store_subscription_send_report


class Command(BaseCommand):
    def handle(self, *args, **options):
        for subscription in StoreSubscription.objects.all():
            store_subscription_send_report.delay(subscription.id)
