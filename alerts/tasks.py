from celery import shared_task

from .models import ProductPriceAlert


@shared_task(queue='general', ignore_result=True)
def alert_check_for_changes(alert_id):
    ProductPriceAlert.objects.get(pk=alert_id).check_for_changes()


@shared_task(queue='general', ignore_result=True)
def alert_revoke(alert_id):
    ProductPriceAlert.objects.get(pk=alert_id).revoke()
