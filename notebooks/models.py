from django.conf import settings
from django.dispatch import receiver

from metamodel.signals import instance_model_saved


@receiver(instance_model_saved)
def post_save(instance_model, created, creator_id, **kwargs):
    if instance_model.model.name == 'NotebookVideoCard':
        es = settings.ES
        document, keywords = instance_model.elasticsearch_document()
        es.index(index='notebook-videocards',
                 doc_type='NotebookVideoCard',
                 id=instance_model.id,
                 body=document)
    elif instance_model.model.name == 'NotebookProcessor':
        es = settings.ES
        document, keywords = instance_model.elasticsearch_document()
        es.index(index='notebook-processors',
                 doc_type='NotebookProcessor',
                 id=instance_model.id,
                 body=document)
