from django.db import models

from metamodel.models import InstanceModel
from solotodo.models import CategorySpecsFilter, Category, ApiClient, \
    CategorySpecsOrder, Country


class CategorySpecsFormLayout(models.Model):
    category = models.ForeignKey(Category)
    api_client = models.ForeignKey(ApiClient, blank=True, null=True)
    country = models.ForeignKey(Country, blank=True, null=True)
    name = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        result = str(self.category)
        if self.api_client:
            result += ' - ' + str(self.api_client)
        if self.country:
            result += ' - ' + str(self.country)
        if self.name:
            result += ' - ' + self.name
        return result

    class Meta:
        ordering = ('category', 'api_client', 'country', 'name')


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
    continuous_range_step = models.IntegerField(blank=True, null=True)
    continuous_range_unit = models.CharField(max_length=20, blank=True,
                                             null=True)

    def __str__(self):
        return '{} - {}'.format(self.fieldset, self.label)

    def choices(self):
        meta_model = self.filter.meta_model
        if meta_model.is_primitive():
            return None
        else:
            return meta_model.instancemodel_set.all()

    class Meta:
        ordering = ('fieldset', 'ordering')


class CategorySpecsFormOrder(models.Model):
    layout = models.ForeignKey(CategorySpecsFormLayout, related_name='orders')
    order = models.ForeignKey(CategorySpecsOrder)
    label = models.CharField(max_length=100)
    ordering = models.IntegerField()
    suggested_use = models.CharField(max_length=20, choices=[
        ('ascending', 'Ascending'),
        ('descending', 'Descending'),
        ('both', 'Both'),
    ])

    def __str__(self):
        return '{} - {}'.format(self.layout, self.label)

    class Meta:
        ordering = ('layout', 'ordering')


class CategorySpecsFormColumn(models.Model):
    layout = models.ForeignKey(CategorySpecsFormLayout, related_name='columns')
    label = models.CharField(max_length=100)
    field = models.CharField(max_length=100)
    ordering = models.IntegerField()

    def __str__(self):
        return '{} - {}'.format(self.layout, self.label)

    class Meta:
        ordering = ('layout', 'ordering')
