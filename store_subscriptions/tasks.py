from celery import shared_task

from .models import StoreSubscription


@shared_task(queue='reports', ignore_result=True)
def store_subscription_send_report(subscription_id):
    StoreSubscription.objects.get(pk=subscription_id).send_report()
