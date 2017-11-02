from decimal import Decimal
from django import forms
from django.db.models import Count, Sum
from rest_framework.reverse import reverse

from solotodo.models import Store, Category, Entity, Product
from solotodo.serializers import EntityWithInlineProductSerializer, \
    NestedProductSerializer


def create_generic_serializer(view_name):
    class GenericSerializer(object):
        def __init__(self, instances, request, *args, **kwargs):
            super(GenericSerializer, self).__init__()
            data = {}

            for instance in instances:
                data[instance.id] = reverse(
                    view_name, kwargs={'pk': instance.pk}, request=request)

            self.data = data

        def to_dict(self):
            return self.data

    return GenericSerializer


def serializer_wrapper(serializer):
    class WrappedSerializer(object):
        def __init__(self, instances, request):
            data = {}
            entries = serializer(instances, many=True,
                                 context={'request': request}).data

            for entry in entries:
                data[entry['id']] = entry

            self.data = data

        def to_dict(self):
            return self.data

    return WrappedSerializer


class LeadGroupingForm(forms.Form):
    CHOICES = [
        ('store', 'Store'),
        ('date', 'Date'),
        ('category', 'Category'),
        ('entity', 'Entity'),
        ('product', 'Product'),
    ]

    grouping = forms.MultipleChoiceField(
        choices=CHOICES
    )

    ORDERING_CHOICES = [
        ('count', 'Lead count'),
        ('normal_price_sum', 'Sum of normal prices'),
        ('offer_price_sum', 'Sum of offer prices'),
    ]

    ordering = forms.ChoiceField(
        choices=ORDERING_CHOICES,
        required=False
    )

    def aggregate(self, request, qs):
        groupings = self.cleaned_data['grouping']

        conversion_dict = {
            'store': {
                'field': 'entity_history__entity__store',
                'serializer': create_generic_serializer('store-detail'),
                'queryset': Store.objects.all()
            },
            'date': {
                'field': 'date',
                'serializer': None,
                'queryset': None
            },
            'category': {
                'field': 'entity_history__entity__category',
                'serializer': create_generic_serializer('category-detail'),
                'queryset': Category.objects.all()
            },
            'entity': {
                'field': 'entity_history__entity',
                'serializer': serializer_wrapper(
                    EntityWithInlineProductSerializer),
                'queryset': Entity.objects.select_related(
                    'store', 'category',
                    'product__instance_model__model__category')
            },
            'product': {
                'field': 'entity_history__entity__product',
                'serializer': serializer_wrapper(
                    NestedProductSerializer),
                'queryset': Product.objects.select_related(
                    'instance_model__model__category')
            }
        }

        aggregation_fields = [conversion_dict[grouping]['field']
                              for grouping in groupings]

        ordering = self.cleaned_data['ordering']
        if ordering:
            ordering = ['-' + ordering]
        else:
            ordering = aggregation_fields

        agg_result = qs \
            .extra(select={'date': 'DATE(solotodo_lead.timestamp)'})\
            .values(*aggregation_fields)\
            .annotate(
                count=Count('id'),
                normal_price_sum=Sum('entity_history__normal_price'),
                offer_price_sum=Sum('entity_history__offer_price')
            )\
            .order_by(*ordering)

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
                'normal_price_sum': str(Decimal(entry['normal_price_sum'])),
                'offer_price_sum': str(Decimal(entry['offer_price_sum']))
            }

            for grouping in groupings:
                field = conversion_dict[grouping]['field']
                cleaned_value = grouping_cleaned_values[grouping][entry[field]]
                subresult[grouping] = cleaned_value

            result.append(subresult)

        return result
