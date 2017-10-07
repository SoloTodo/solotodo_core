from django.db import models
from .category import Category


class CategorySpecsOrder(models.Model):
    category = models.ForeignKey(Category)
    name = models.CharField(max_length=100)
    es_field = models.CharField(max_length=100)

    def __str__(self):
        return '{} - {}'.format(self.category, self.name)

    class Meta:
        app_label = 'solotodo'
        ordering = ('category', 'name')
