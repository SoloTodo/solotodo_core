from django.db import models

from hardware.models.budget import Budget
from solotodo.models import Category, Store, Entity


class BudgetEntry(models.Model):
    budget = models.ForeignKey(Budget, on_delete=models.CASCADE,
                               related_name='entries')
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    selected_entity = models.ForeignKey(Entity, on_delete=models.SET_NULL,
                                        null=True, blank=True)

    def __str__(self):
        return u'{} - {} - {}'.format(self.budget, self.category,
                                      self.selected_entity)

    class Meta:
        app_label = 'hardware'
        ordering = ['budget', 'category']
