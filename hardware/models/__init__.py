from django.db.models.signals import post_save

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
