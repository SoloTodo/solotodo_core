from django import forms
from elasticsearch_dsl import Q, A

from solotodo.models import Category
from solotodo.utils import recursive_dict_search


class ProductSpecsForm(forms.Form):
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
        return {'_score': 'asc'}

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

    # This is the exact same implementation than CategorySpecsForm
    def flatten_es_aggs(self, aggs):
        flatened_aggs = {}
        for spec_field_name in self.get_field_names():
            if spec_field_name in aggs:
                base_agg_data = aggs[spec_field_name]
                agg_data = recursive_dict_search(base_agg_data, 'buckets')
            else:
                agg_data = recursive_dict_search(
                    aggs['all_filtered_products'][spec_field_name],
                    'buckets')

            flatened_aggs[spec_field_name] = [{
                'id': x['key'],
                'doc_count': x['doc_count']
            } for x in agg_data]
        return flatened_aggs