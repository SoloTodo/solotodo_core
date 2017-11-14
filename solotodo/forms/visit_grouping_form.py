from django import forms
from django.db.models import Count

from solotodo.forms.lead_grouping_form import create_generic_serializer, \
    serializer_wrapper
from solotodo.models import Category, Product
from solotodo.serializers import NestedProductSerializerWithCategory


class VisitGroupingForm(forms.Form):
    CHOICES = [
        ('date', 'Date'),
        ('category', 'Category'),
        ('product', 'Product'),
    ]

    grouping = forms.MultipleChoiceField(
        choices=CHOICES
    )

    def aggregate(self, request, qs):
        groupings = self.cleaned_data['grouping']

        conversion_dict = {
            'date': {
                'field': 'date',
                'serializer': None,
                'queryset': None
            },
            'category': {
                'field': 'product__instance_model__model__category',
                'serializer': create_generic_serializer('category-detail'),
                'queryset': Category.objects.all()
            },
            'product': {
                'field': 'product',
                'serializer': serializer_wrapper(
                    NestedProductSerializerWithCategory),
                'queryset': Product.objects.select_related(
                    'instance_model__model__category')
            }
        }

        aggregation_fields = [conversion_dict[grouping]['field']
                              for grouping in groupings]

        agg_result = qs \
            .extra(select={'date': 'DATE(solotodo_visit.timestamp)'})\
            .values(*aggregation_fields)\
            .annotate(count=Count('id'))\
            .order_by('-count')

        result = []

        grouping_values = {grouping: set() for grouping in groupings}

        for entry in agg_result:
            for grouping in groupings:
                grouping_values[grouping].add(
                    entry[conversion_dict[grouping]['field']])

        grouping_cleaned_values = {}

        for grouping in groupings:
            values = grouping_values[grouping]

            conversion_qs = conversion_dict[grouping]['queryset']

            if conversion_qs:
                cleaned_values = conversion_qs.filter(
                    pk__in=grouping_values[grouping])
            else:
                cleaned_values = values

            serializer_class = conversion_dict[grouping]['serializer']

            if serializer_class:
                serialized_values = serializer_class(cleaned_values,
                                                     request=request).to_dict()
            else:
                serialized_values = {value: value for value in cleaned_values}

            grouping_cleaned_values[grouping] = serialized_values

        for entry in agg_result:
            subresult = {
                'count': entry['count'],
            }

            for grouping in groupings:
                field = conversion_dict[grouping]['field']
                cleaned_value = grouping_cleaned_values[grouping][entry[field]]
                subresult[grouping] = cleaned_value

            result.append(subresult)

        return result
