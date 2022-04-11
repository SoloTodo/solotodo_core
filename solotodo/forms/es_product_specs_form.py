from django import forms
from elasticsearch_dsl import Q, A

from solotodo.models import Category


class EsProductSpecsForm(forms.Form):
    categories = forms.ModelMultipleChoiceField(
        queryset=Category.objects.all(),
        required=False
    )

    def get_field_names(self):
        return ['categories']

    def get_filter(self, skip=None):
        if skip == 'categories':
            return Q()

        categories = self.cleaned_data['categories']

        if not categories:
            return Q()

        return Q('terms', category_id=[x.id for x in categories])

    def get_ordering(self):
        return '_score'

    def get_aggregation_buckets(self):
        empty_filter = Q()
        category_filter = self.get_filter()
        all_filtered_bucket = A('filter', filter=category_filter)
        active_filters_buckets = {}

        if category_filter == empty_filter:
            bucket = A('terms',
                       field='category_id',
                       size=100)
            all_filtered_bucket.bucket('categories', bucket)
        else:
            bucket = A(
                'terms',
                field='category_id',
                size=100)

            active_filters_buckets['categories'] = bucket

        return all_filtered_bucket, active_filters_buckets
