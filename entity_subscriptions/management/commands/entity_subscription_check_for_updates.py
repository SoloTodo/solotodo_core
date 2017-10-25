from django.core.management import BaseCommand

from entity_subscriptions.models import EntitySubscription
from entity_subscriptions.tasks import entity_subscription_check_for_updates


class Command(BaseCommand):
    def handle(self, *args, **options):
        for entity_susbcription in EntitySubscription.objects.all():
            entity_subscription_check_for_updates.delay(entity_susbcription.id)
