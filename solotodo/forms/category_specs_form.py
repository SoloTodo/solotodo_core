from django import forms
from django.core.exceptions import ValidationError
from elasticsearch_dsl import Q, A

from solotodo.models import EsProduct
from solotodo.utils import recursive_dict_search


class CategorySpecsForm(forms.Form):
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

    def get_field_names(self):
        return [x.name for x in self.category_specs_filters]

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

            spec_filter = field.es_filter(self.cleaned_data)

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

        ordering_string = self.ordering_value_to_es_field_dict[ordering]

        if ordering_string.startswith('-'):
            order_field = ordering_string[1:]
            order_direction = 'desc'
        else:
            order_field = ordering_string
            order_direction = 'asc'

        return {order_field: order_direction}

    def get_aggregation_buckets(self):
        # Returns a tuple of two elements
        #
        # The first is an ES DSL bucket (A object) that contains the
        # aggregations of all inactive filters
        # The second is a dictionary {field_name => Agg object} that represents
        # the aggregations of the active filters. These aggregations consider
        # the fact that when we filter by a field (brand "HP" for example)
        # we want the aggregations for that field to consider the other
        # options as well (brands "Apple", "ASUS", etc)
        empty_filter = Q()
        all_filters = self.get_filter()
        all_filtered_bucket = A('filter', filter=all_filters)
        active_filters_buckets = {}

        for category_spec_filter in self.category_specs_filters:
            spec_filter = category_spec_filter.es_filter(
                self.cleaned_data)
            spec_bucket = category_spec_filter.aggregation_bucket()

            if spec_filter == empty_filter:
                all_filtered_bucket.bucket(category_spec_filter.name, spec_bucket)
            else:
                other_active_filters = self.get_filter(
                    skip=category_spec_filter.name)
                bucket = A('filter', filter=other_active_filters)
                bucket.bucket(spec_filter.name, spec_bucket)

                active_filters_buckets[category_spec_filter.name] = bucket

        return all_filtered_bucket, active_filters_buckets

    def get_es_products(self, search=None):
        from solotodo.models import Product

        if not self.is_valid():
            raise ValidationError(self.errors)

        if not search:
            search = EsProduct.category_search(self.category)

        keywords = self.cleaned_data['search']

        if keywords:
            keywords_query = Product.query_es_by_search_string(keywords,
                                                               mode='AND')
            search = search.query(keywords_query)

        all_filters = self.get_filter()
        search = search.filter(all_filters)
        ordering = self.get_ordering()

        if ordering:
            search = search.sort(ordering)

        all_filtered_bucket, active_filters_buckets = self.get_aggregation_buckets()
        search.aggs.bucket('all_filtered_products', all_filtered_bucket)
        for field_name, bucket in active_filters_buckets.items():
            search.aggs.bucket(field_name, bucket)

        return search

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
