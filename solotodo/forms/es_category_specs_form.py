# TODO: Remove this class as it will be replace with a full ES Version

from django import forms
from django.core.exceptions import ValidationError
from elasticsearch_dsl import Q, A


class EsCategorySpecsForm(forms.Form):
    ordering = forms.ChoiceField(choices=[], required=False)
    search = forms.CharField(required=False)

    @classmethod
    def add_filter(cls, category_specs_filter):
        cls.base_fields.update(category_specs_filter.form_fields_dict())
        cls.category_specs_filters.append(category_specs_filter)

    @classmethod
    def add_order(cls, category_specs_order):
        ordering_field = category_specs_order.es_field
        for prefix in ['', '-']:
            new_ordering_name = prefix + category_specs_order.name
            new_ordering_field = '{}specs.{}'.format(prefix, ordering_field)

            cls.base_fields['ordering'].choices.append(
                (new_ordering_name, new_ordering_field))
            cls.ordering_value_to_es_field_dict[new_ordering_name] = \
                new_ordering_field

    def get_filter(self, skip=None):
        # Returns the ElasticSearch DSL query object that represents
        # the application of all of the filters represented by this form
        # Accepts an optional "skip" parameter that represents the name of a
        # field that must not be skipped when assembling the filter.
        # This is useful for the faceting part of the products browse query
        # that needs to ignore a particular field to get all of its facets.

        specs_filter = Q()
        empty_filter = Q()

        for field in self.category_specs_filters:
            if field.name == skip:
                continue

            spec_filter = field.es_filter(self.cleaned_data, prefix='specs.')

            if spec_filter == empty_filter:
                continue

            specs_filter &= spec_filter
        return specs_filter

    def get_ordering(self):
        # If the form has a ordering value, returns a ElasticSearch DSL
        # compatible string for sorting the results of a ElasticSearch
        # DSL search object
        # e.g. search.sort(...)
        # Otherwise returns None

        ordering = self.cleaned_data['ordering']

        if not ordering:
            return None

        return self.ordering_value_to_es_field_dict[ordering]

    def get_es_products(self, search):
        from solotodo.models import Product

        if not self.is_valid():
            raise ValidationError(self.errors)

        keywords = self.cleaned_data['search']

        if keywords:
            keywords_query = Product.query_es_by_search_string(keywords,
                                                               mode='AND')
            search = search.query(keywords_query)

        bucket_field = self.cleaned_data['bucket_field']

        search_bucket_agg = None
        if bucket_field:
            search_bucket_agg = A('terms', field=bucket_field, size=10000)

        fields_es_filters_dict = {
            field: field.es_filter(self.cleaned_data, prefix='specs.')
            for field in self.category_specs_filters
        }

        all_filters = Q()

        for field in self.category_specs_filters:
            aggs_filters = Q()

            other_fields = [f for f in self.category_specs_filters
                            if f != field]
            for other_field in other_fields:
                aggs_filters &= fields_es_filters_dict[other_field]

            field_bucket = A('terms', field='specs.' + field.es_id_field(),
                             size=1000)

            if search_bucket_agg:
                # 'search_bucket' is just a name, just need to be consistent
                # later
                field_bucket.bucket('search_bucket', search_bucket_agg)

            agg = A('filter', filter=aggs_filters)
            agg.bucket('result', field_bucket)

            search.aggs.bucket(field.name, agg)
            search = search.post_filter(fields_es_filters_dict[field])

            all_filters &= fields_es_filters_dict[field]

        search.aggs.bucket('filtered_products', 'filter', filter=all_filters)

        ordering = self.cleaned_data['ordering']

        if ordering:
            search = search.sort(
                self.ordering_value_to_es_field_dict[ordering])

        return search

    def process_es_aggs(self, aggs):
        new_aggs = {}

        for field in self.category_specs_filters:
            field_name = field.name

            new_aggs[field_name] = [{
                'id': field_agg['key'],
                'doc_count': field_agg['doc_count']
            } for field_agg in aggs[field_name]['result']['buckets']]

        return new_aggs
