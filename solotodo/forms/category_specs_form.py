import json

from django import forms
from elasticsearch_dsl import Q, A

from solotodo.utils import iterable_to_dict


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
            new_ordering_field = prefix + ordering_field

            cls.base_fields['ordering'].choices.append(
                (new_ordering_name, new_ordering_field))
            cls.ordering_value_to_es_field_dict[new_ordering_name] = \
                new_ordering_field

    def get_es_products(self):
        from solotodo.models import Product

        assert self.is_valid()

        es_search = self.category.es_search()

        search = self.cleaned_data['search']
        if search:
            es_search = Product.query_es_by_search_string(
                es_search, search, mode='AND')

        fields_es_filters_dict = {
            field: field.es_filter(self.cleaned_data)
            for field in self.category_specs_filters
        }

        for field in self.category_specs_filters:
            aggs_filters = Q()

            other_fields = [f for f in self.category_specs_filters
                            if f != field]
            for other_field in other_fields:
                aggs_filters &= fields_es_filters_dict[other_field]

            field_agg = A('terms', field=field.es_id_field(), size=1000)

            agg = A('filter', aggs_filters)
            # "result" is just a name, we could've named the bucket "foo"
            # just need to be consistent when querying the aggs later
            agg.bucket('result', field_agg)

            es_search.aggs.bucket(field.name, agg)
            es_search = es_search.post_filter(fields_es_filters_dict[field])

        ordering = self.cleaned_data['ordering']

        if ordering:
            es_search = es_search.sort(
                self.ordering_value_to_es_field_dict[ordering])
        else:
            es_search = es_search.sort('unicode.keyword')

        print(json.dumps(es_search.to_dict(), indent=2))

        return es_search

    def process_es_aggs(self, aggs):
        category_fields_specs_dict = iterable_to_dict(
            self.category_specs_filters, 'name')

        new_aggs = {}

        for field_name, field_aggs in aggs.to_dict().items():
            buckets = field_aggs['result']['buckets']
            field = category_fields_specs_dict[field_name]
            new_field_aggs = field.process_buckets(buckets)
            new_aggs[field.name] = new_field_aggs

        return new_aggs
