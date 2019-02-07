from celery import shared_task

from .models import AnonymousAlert


@shared_task(queue='general', ignore_result=True)
def anonymous_alert_check_for_changes(alert_id):
    AnonymousAlert.objects.get(pk=alert_id).check_for_changes()
