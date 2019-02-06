from celery import shared_task

from .models import Alert


@shared_task(queue='general', ignore_result=True)
def alert_check_for_changes(alert_id):
    Alert.objects.get(pk=alert_id).check_for_changes()
