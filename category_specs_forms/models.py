from django.db import models

from solotodo.models import CategorySpecsFilter, Category, ApiClient, \
    CategorySpecsOrder


class CategorySpecsFormLayout(models.Model):
    category = models.ForeignKey(Category)
    api_client = models.ForeignKey(ApiClient)
    name = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        result = '{} - {}'.format(self.category, self.api_client)
        if self.name:
            result += ' - ' + self.name
        return result

    class Meta:
        ordering = ('category', 'api_client', 'name')


class CategorySpecsFormFieldset(models.Model):
    layout = models.ForeignKey(CategorySpecsFormLayout,
                               related_name='fieldsets')
    label = models.CharField(max_length=100)
    ordering = models.IntegerField()

    def __str__(self):
        return '{} - {}'.format(self.layout, self.label)

    class Meta:
        ordering = ('layout', 'ordering')


class CategorySpecsFormFilter(models.Model):
    fieldset = models.ForeignKey(CategorySpecsFormFieldset,
                                 related_name='filters')
    filter = models.ForeignKey(CategorySpecsFilter)
    label = models.CharField(max_length=100)
    ordering = models.IntegerField()

    def __str__(self):
        return '{} - {}'.format(self.fieldset, self.label)

    class Meta:
        ordering = ('fieldset', 'ordering')


class CategorySpecsFormOrder(models.Model):
    layout = models.ForeignKey(CategorySpecsFormLayout, related_name='orders')
    order = models.ForeignKey(CategorySpecsOrder)
    label = models.CharField(max_length=100)
    ordering = models.IntegerField()
    suggested_use = models.CharField(max_length=20, choices=[
        ('gte', 'High to low'),
        ('lte', 'Low to high'),
        ('both', 'Both'),
    ])

    def __str__(self):
        return '{} - {}'.format(self.layout, self.label)

    class Meta:
        ordering = ('layout', 'ordering')
