from django.db import models

from metamodel.models import InstanceModel
from solotodo.models import CategorySpecsFilter, Category, Website, \
    CategorySpecsOrder, Country


class CategorySpecsFormLayout(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    website = models.ForeignKey(Website, on_delete=models.CASCADE,
                                blank=True, null=True)
    name = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        result = str(self.category)
        if self.website:
            result += ' - ' + str(self.website)
        if self.name:
            result += ' - ' + self.name
        return result

    class Meta:
        ordering = ('category', 'website', 'name')


class CategorySpecsFormFieldset(models.Model):
    layout = models.ForeignKey(CategorySpecsFormLayout,
                               on_delete=models.CASCADE,
                               related_name='fieldsets')
    label = models.CharField(max_length=100)
    ordering = models.IntegerField()

    def __str__(self):
        return '{} - {}'.format(self.layout, self.label)

    class Meta:
        ordering = ('layout', 'ordering')


class CategorySpecsFormFilter(models.Model):
    fieldset = models.ForeignKey(CategorySpecsFormFieldset,
                                 on_delete=models.CASCADE,
                                 related_name='filters')
    filter = models.ForeignKey(CategorySpecsFilter, on_delete=models.CASCADE)
    country = models.ForeignKey(Country, on_delete=models.CASCADE,
                                blank=True, null=True)
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
    layout = models.ForeignKey(CategorySpecsFormLayout,
                               on_delete=models.CASCADE, related_name='orders')
    order = models.ForeignKey(CategorySpecsOrder, on_delete=models.CASCADE)
    country = models.ForeignKey(Country,
                                on_delete=models.CASCADE,
                                blank=True, null=True)
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
