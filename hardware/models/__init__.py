from django.conf import settings
from django.db.models.signals import post_save

from metamodel.signals import instance_model_saved
from .budget import Budget
from .budget_entry import BudgetEntry


def create_budget_entries(sender, instance, created, **kwargs):
    from solotodo.models import Category

    if created:
        budget_categories = Category.objects.filter(
            budget_ordering__isnull=False).order_by('budget_ordering')
        for category in budget_categories:
            BudgetEntry.objects.create(
                budget=instance,
                category=category
            )


post_save.connect(create_budget_entries, sender=Budget)


def handle_instance_model_saved(instance_model, created, creator_id, **kwargs):
    if instance_model.model.name == 'VideoCardGpu':
        es = settings.ES
        document, keywords = instance_model.elasticsearch_document()
        es.index(index='videocard-gpus',
                 id=instance_model.id,
                 body=document)


instance_model_saved.connect(handle_instance_model_saved)
