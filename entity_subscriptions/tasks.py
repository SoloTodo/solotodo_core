from celery import shared_task

from entity_subscriptions.models import EntitySubscription


@shared_task(queue='general', ignore_result=True)
def entity_subscription_check_for_updates(entity_subscription_id):
    entity_subscription = EntitySubscription.objects.get(
        pk=entity_subscription_id)
    entity_subscription.check_for_updates()
