from django.conf import settings
from celery import shared_task

from metamodel.models import InstanceModel


@shared_task(queue='general', ignore_result=True)
def video_card_gpu_save(instance_model_id, update_scores=True):
    instance_model = InstanceModel.objects.get(pk=instance_model_id)

    # Create or update the elasticsearch entry for the GPU, as it is not
    # a Product so we must handle it manually
    es = settings.ES
    document, keywords = instance_model.elasticsearch_document()
    es.index(index='videocard-gpus',
             # doc_type='GPU',
             id=instance_model.id,
             body=document)
