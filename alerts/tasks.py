from celery import shared_task

from .models import AnonymousAlert, UserAlert, ProductPriceAlert


@shared_task(queue='general', ignore_result=True)
def anonymous_alert_check_for_changes(alert_id):
    AnonymousAlert.objects.get(pk=alert_id).check_for_changes()


@shared_task(queue='general', ignore_result=True)
def user_alert_check_for_changes(alert_id):
    UserAlert.objects.get(pk=alert_id).check_for_changes()


@shared_task(queue='general', ignore_result=True)
def alert_check_for_changes(alert_id):
    ProductPriceAlert.objects.get(pk=alert_id).check_for_changes()
