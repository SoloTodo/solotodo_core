from django import forms
from django_filters.fields import IsoDateTimeField

from solotodo.forms.lead_grouping_form import create_generic_serializer, \
    serializer_wrapper
from solotodo.serializers import NestedProductSerializer, \
    EntityMinimalSerializer, EntityWithInlineProductSerializer


class EntityEstimatedSalesForm(forms.Form):
    GROUPING_CHOICES = [
        ('store', 'Store'),
        ('category', 'Category'),
        ('product', 'Product'),
        ('entity', 'Entity'),
    ]

    grouping = forms.ChoiceField(
        choices=GROUPING_CHOICES,
        required=False
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
    timestamp_after = IsoDateTimeField(required=False)
    timestamp_before = IsoDateTimeField(required=False)

    def estimated_sales(self, qs, request):
        entity_values = qs.select_related(
                'store',
                'product__instance_model__model__category',
                'category', 'currency')\
            .estimated_sales(self.cleaned_data['timestamp_after'],
                             self.cleaned_data['timestamp_before'])

        preferred_currency = request.user.preferred_currency_or_default()

        grouping = self.cleaned_data['grouping']
        if not grouping:
            grouping = 'entity'

        conversion_dict = {
            'store': {
                'field': 'store',
                'serializer': create_generic_serializer('store-detail'),
            },
            'category': {
                'field': 'category',
                'serializer': create_generic_serializer('category-detail')
            },
            'product': {
                'field': 'product',
                'serializer': serializer_wrapper(NestedProductSerializer),
            },
            'entity': {
                'field': None,
                'serializer': serializer_wrapper(
                    EntityWithInlineProductSerializer),
            }
        }

        field = conversion_dict[grouping]['field']

        group_values_dict = {}

        for entry in entity_values:
            entity = entry['entity']

            exchange_rate = preferred_currency.exchange_rate / \
                entity.currency.exchange_rate

            if field:
                group = getattr(entity, field)
            else:
                group = entity
            if not group:
                continue
            if group not in group_values_dict:
                group_values_dict[group] = {
                    'count': 0,
                    'normal_price_sum': 0,
                    'offer_price_sum': 0
                }
            group_values_dict[group]['count'] += entry['count']
            group_values_dict[group]['normal_price_sum'] += \
                exchange_rate * entry['normal_price_sum']
            group_values_dict[group]['offer_price_sum'] += \
                exchange_rate * entry['offer_price_sum']

        ordering = self.cleaned_data['ordering']
        if not ordering:
            ordering = 'count'

        sorted_result = sorted(group_values_dict.items(),
                               key=lambda x: x[1][ordering], reverse=True)

        serializer_klass = conversion_dict[grouping]['serializer']
        serialized_groups_dict = serializer_klass(
            group_values_dict.keys(), request).to_dict()

        result = []
        for group, values in sorted_result:
            group_values = {
                grouping: serialized_groups_dict[group.id],
                'count': values['count'],
                'normal_price_sum': values['normal_price_sum'],
                'offer_price_sum': values['offer_price_sum'],
            }
            result.append(group_values)

        return result
