from celery import shared_task

from solotodo.models import Store


@shared_task(queue='store_update', ignore_result=True)
def store_update_banners(store_id):
    Store.objects.get(pk=store_id).update_banners()
