from django.db import models

from solotodo.models import Category, Country


class CategoryField(models.Model):
    category = models.ForeignKey(Category)
    es_field = models.CharField(max_length=100)
    label = models.CharField(max_length=100)

    def __str__(self):
        return '{} - {} - {}'.format(self.category, self.label, self.es_field)

    class Meta:
        ordering = ('category', 'label', 'es_field')


class CategoryColumnPurpose(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ('name', )


class CategoryColumn(models.Model):
    field = models.ForeignKey(CategoryField)
    purpose = models.ForeignKey(CategoryColumnPurpose)
    country = models.ForeignKey(Country, blank=True, null=True)
    ordering = models.PositiveIntegerField()

    def __str__(self):
        return '{} - {}'.format(self.field, self.purpose)

    class Meta:
        ordering = ('field__category', 'ordering')
