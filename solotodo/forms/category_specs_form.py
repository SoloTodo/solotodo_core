# TODO: Remove this class as it will be replace with a full ES Version

from django import forms
from django.core.exceptions import ValidationError
from elasticsearch_dsl import Q, A

from solotodo.models import EsProduct


class CategorySpecsForm(forms.Form):
    ordering = forms.ChoiceField(choices=[], required=False)

    @classmethod
    def add_filter(cls, category_specs_filter):
        cls.base_fields.update(category_specs_filter.form_fields_dict())
        cls.category_specs_filters.append(category_specs_filter)

    @classmethod
    def add_order(cls, category_specs_order):
        ordering_field = category_specs_order.es_field
        for prefix in ['', '-']:
            new_ordering_name = prefix + category_specs_order.name
            new_ordering_field = prefix + 'specs.' + ordering_field

            cls.base_fields['ordering'].choices.append(
                (new_ordering_name, new_ordering_field))
            cls.ordering_value_to_es_field_dict[new_ordering_name] = \
                new_ordering_field

    def get_es_products(self, es_search=None):
        from solotodo.models import Product

        if not self.is_valid():
            raise ValidationError(self.errors)

        if not es_search:
            es_search = EsProduct.category_search(self.category)

        search = self.cleaned_data['search']
        if search:
            q = Product.query_es_by_search_string(search, mode='AND')
            es_search = es_search.filter(q)

        fields_es_filters_dict = {
            field: field.es_filter(self.cleaned_data, prefix='specs.')
            for field in self.category_specs_filters
        }

        bucket_field = self.cleaned_data['bucket_field']

        search_bucket_agg = None
        if bucket_field:
            search_bucket_agg = A('terms', field='specs.' + bucket_field,
                                  size=10000)

        for field in self.category_specs_filters:
            aggs_filters = Q()

            other_fields = [f for f in self.category_specs_filters
                            if f != field]
            for other_field in other_fields:
                aggs_filters &= fields_es_filters_dict[other_field]

            field_agg = A('terms', field='specs.' + field.es_id_field(),
                          size=1000)

            if search_bucket_agg:
                # 'search_bucket' is just a name, just need to be consistent
                # later
                field_agg.bucket('search_bucket', search_bucket_agg)

            agg = A('filter', aggs_filters)

            # "result" is also just an arbitrary name
            agg.bucket('result', field_agg)

            es_search.aggs.bucket(field.name, agg)
            es_search = es_search.post_filter(fields_es_filters_dict[field])

        ordering = self.cleaned_data['ordering']

        if ordering:
            es_search = es_search.sort(
                self.ordering_value_to_es_field_dict[ordering])
        else:
            es_search = es_search.sort('name.raw')

        return es_search

    def process_es_aggs(self, aggs):
        new_aggs = {}

        for field_name, field_aggs in aggs.to_dict().items():
            new_aggs[field_name] = [{
                'id': field_agg['key'],
                'doc_count': field_agg['doc_count']
            } for field_agg in field_aggs['result']['buckets']]

        return new_aggs
