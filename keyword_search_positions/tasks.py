from celery import shared_task

from .models import KeywordSearch


@shared_task(queue='general', ignore_result=True)
def keyword_search_update(keyword_search_id):
    KeywordSearch.objects.get(pk=keyword_search_id).update()
