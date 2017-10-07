from django.db import models
from django import forms
from elasticsearch_dsl import Q

from metamodel.models import MetaModel
from .category import Category


class CategorySpecsField(models.Model):
    category = models.ForeignKey(Category)
    name = models.CharField(max_length=100)
    meta_model = models.ForeignKey(MetaModel)
    type = models.CharField(max_length=20, choices=[
        ('exact', 'Exact'),
        ('gte', 'Greater than or equal'),
        ('lte', 'Less than or equal'),
        ('range', 'Range (from / to)'),
    ])
    es_field = models.CharField(max_length=100)
    value_field = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return '{} - {}'.format(self.category, self.name)

    @property
    def form_fields_dict(self):
        field_names = []
        if self.type == 'exact':
            field_names = [self.name]
        else:
            if self.type in ['gte', 'range']:
                field_names = ['{}_min'.format(self.name)]
            if self.type in ['lte', 'range']:
                field_names.append('{}_max'.format(self.name))

        if self.type == 'exact':
            if self.meta_model.is_primitive():
                raise Exception('Exact query {} not allowed'.format(self.name))
            else:
                field = forms.ModelMultipleChoiceField(
                    queryset=self.meta_model.instancemodel_set.all(),
                    required=False
                )
        else:
            if self.meta_model.is_primitive():
                field_class = getattr(forms, self.meta_model.name)
                field = field_class(required=False)
            else:
                field = forms.ModelChoiceField(
                    queryset=self.meta_model.instancemodel_set.all(),
                    required=False
                )

        return {field_name: field for field_name in field_names}

    def es_filter(self, form_data):
        result = Q()

        value_field = self.value_field
        if value_field is None:
            if self.type == 'exact':
                value_field = 'id'
            else:
                value_field = 'value'

        if self.type == 'exact' and form_data[self.name]:
            if self.meta_model.is_primitive():
                filter_values = form_data[self.name]
            else:
                filter_values = [getattr(obj, value_field) for obj in
                                 form_data[self.name]]
            result &= Q('terms', **{self.es_field: filter_values})

        if self.type in ['gte', 'range']:
            min_form_field = '{}_min'.format(self.name)
            if form_data[min_form_field]:
                if self.meta_model.is_primitive():
                    filter_value = form_data[min_form_field]
                else:
                    filter_value = getattr(form_data[min_form_field],
                                           value_field)
                result &= Q('range', **{self.es_field: {'gte': filter_value}})

        if self.type in ['lte', 'range']:
            max_form_field = '{}_max'.format(self.name)
            if form_data[max_form_field]:
                if self.meta_model.is_primitive():
                    filter_value = form_data[max_form_field]
                else:
                    filter_value = getattr(form_data[max_form_field],
                                           value_field)
                result &= Q('range', **{self.es_field: {'lte': filter_value}})

        return result

    class Meta:
        app_label = 'solotodo'
        ordering = ('category', 'name')
