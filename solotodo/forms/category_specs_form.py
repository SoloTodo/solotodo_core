from django import forms
from elasticsearch_dsl import Q, A


class CategorySpecsForm(forms.Form):
    @classmethod
    def add_field(cls, category_specs_field):
        cls.base_fields.update(category_specs_field.form_fields_dict)
        cls.category_specs_fields.append(category_specs_field)

    def filter_products(self):
        assert self.is_valid()

        es_search = self.category.es_search()

        fields_es_filters_dict = {
            field: field.es_filter(self.cleaned_data)
            for field in self.category_specs_fields
        }

        for field in self.category_specs_fields:
            aggs_filters = Q()

            other_fields = [f for f in self.category_specs_fields
                            if f != field]
            for other_field in other_fields:
                aggs_filters &= fields_es_filters_dict[other_field]

            agg = A('filter', aggs_filters)
            agg.bucket(field.name, 'terms', field=field.es_field, size=1000)

            es_search.aggs.bucket(field.name, agg)
            es_search = es_search.post_filter(fields_es_filters_dict[field])

        return es_search
