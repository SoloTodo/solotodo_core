from django.db import models

from hardware.models.budget import Budget
from solotodo.models import Category, Store, Product


class BudgetEntry(models.Model):
    budget = models.ForeignKey(Budget, on_delete=models.CASCADE,
                               related_name='entries')
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    selected_product = models.ForeignKey(Product, on_delete=models.CASCADE,
                                         null=True, blank=True)
    selected_store = models.ForeignKey(Store, on_delete=models.CASCADE,
                                       null=True, blank=True)

    def __str__(self):
        return u'{} - {} - {} - {}'.format(
            self.budget, self.category, self.selected_product,
            self.selected_store)

    class Meta:
        app_label = 'hardware'
        ordering = ['budget', 'category__budget_ordering', 'id']
