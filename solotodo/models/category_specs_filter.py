from django.db import models
from django import forms
from elasticsearch_dsl import Q, A

from metamodel.models import MetaModel
from .category import Category


class CategorySpecsFilter(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    meta_model = models.ForeignKey(MetaModel, on_delete=models.CASCADE)
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

    def choices(self):
        # Returns a list of InstanceModel representing the choices for
        # this filter or None if the filter is over a primitive Model
        if self.meta_model.is_primitive():
            return None
        else:
            return self.meta_model.instancemodel_set.all()

    def form_fields_dict(self):
        # Returns a dictionary {field_name: field} representing the Django form
        # field name(s) and actual fields represented by this filter.
        field_names = []
        if self.type == 'exact':
            field_names = [self.name]
        else:
            if self.type in ['gte', 'range']:
                field_names = ['{}_min'.format(self.name)]
            if self.type in ['lte', 'range']:
                field_names.append('{}_max'.format(self.name))

        if self.type == 'exact':
            if self.meta_model.name == 'BooleanField':
                field = forms.IntegerField(
                    required=False
                )
            elif self.meta_model.is_primitive():
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

    def cleaned_value_field(self):
        # Returns the normalized value_field for this filter.
        # For exact queries ("processor", "video_card") this is
        # usually "id", otherwise (greater than, less than, ranges)
        # the field is usually "value" ("screen_size", etc)
        if self.value_field:
            return self.value_field

        if self.type == 'exact':
            return 'id'
        else:
            return 'value'

    def es_value_field(self, field=None):
        # Returns the full path to the field in the ElasticSearch object for a particular
        # field ('id' for example). If not given it determines the field with the numeric
        # value of the filter ("id" for most non-primitive filters) and uses it.
        es_field = self.es_field

        if self.meta_model.is_primitive():
            return es_field
        elif es_field.endswith('.id'):
            # This is the particular case when querying a nested field directly
            # (without going further down in the nested tree). For example when filtering
            # notebooks by specific video_card
            return es_field
        else:
            return '{}_{}'.format(es_field, field or self.cleaned_value_field())

    def es_filter(self, form_data):
        # Returns the ES DSL Query (Q object) the represents the application of this
        # filter with the given form data.
        result = Q()

        mm_value_field = self.cleaned_value_field()
        es_value_field = 'specs.{}'.format(self.es_value_field())

        if self.type == 'exact' and form_data[self.name] is not None:
            if self.meta_model.is_primitive():
                # The only exact primitive filter is BooleanField
                filter_values = [bool(form_data[self.name])]
            else:
                filter_values = [getattr(obj, mm_value_field) for obj in
                                 form_data[self.name]]

            if filter_values:
                result &= Q('terms', **{es_value_field: filter_values})

        if self.type in ['gte', 'range']:
            min_form_field = '{}_min'.format(self.name)
            if form_data[min_form_field] is not None:
                if self.meta_model.is_primitive():
                    filter_value = form_data[min_form_field]
                else:
                    filter_value = getattr(form_data[min_form_field],
                                           mm_value_field)
                result &= Q('range', **{es_value_field: {'gte': filter_value}})

        if self.type in ['lte', 'range']:
            max_form_field = '{}_max'.format(self.name)
            if form_data[max_form_field] is not None:
                if self.meta_model.is_primitive():
                    filter_value = form_data[max_form_field]
                else:
                    filter_value = getattr(form_data[max_form_field],
                                           mm_value_field)
                result &= Q('range', **{es_value_field: {'lte': filter_value}})

        # Create the nested query if necessary, but if we are not actually filtering
        # (empty query) there is no need.
        if self._is_es_nested() and result != Q():
            path = 'specs.{}'.format(self.es_field.split('.')[0])
            result = Q('nested', path=path, query=result)

        return result

    def aggregation_bucket(self):
        # Returns the ES DSL Aggregation object (A) that represents the
        # aggregation of a ES search on this field
        term_field = 'specs.{}'.format(self.es_value_field('id'))
        spec_bucket = A('terms', field=term_field, size=100)

        if self._is_es_nested():
            path = 'specs.{}'.format(self.es_field.split('.')[0])
            bucket = A('nested', path=path)
            bucket.bucket('nested_field', spec_bucket)

            return bucket
        else:

            return spec_bucket

    def _is_es_nested(self):
        # Returns True if the filter queries for a field inside a nested
        # field in the ES object representing the object
        return '.' in self.es_field

    class Meta:
        app_label = 'solotodo'
        ordering = ('category', 'name')
