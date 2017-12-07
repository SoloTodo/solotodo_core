from django.db import models

from solotodo.models import Category, Country


class CategoryField(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
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
    field = models.ForeignKey(CategoryField, on_delete=models.CASCADE)
    purpose = models.ForeignKey(CategoryColumnPurpose,
                                on_delete=models.CASCADE)
    country = models.ForeignKey(Country, on_delete=models.CASCADE,
                                blank=True, null=True)
    ordering = models.PositiveIntegerField()

    def __str__(self):
        return '{} - {}'.format(self.field, self.purpose)

    class Meta:
        ordering = ('field__category', 'purpose', 'ordering')
