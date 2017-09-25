from decimal import Decimal
from django import forms
from django.db.models import Count, Sum


class EntityVisitGroupingForm(forms.Form):
    CHOICES = [
        ('store', 'Store'),
        ('date', 'Date'),
    ]

    grouping = forms.MultipleChoiceField(
        choices=CHOICES,
        required=False
    )

    def aggregate_visits(self, qs):
        groupings = self.cleaned_data['grouping']

        conversion_dict = {
            'store': 'entity_history__entity__store',
            'date': 'date'
        }

        qs_values_args = [conversion_dict[grouping] for grouping in groupings]

        agg_result = qs \
            .extra(select={'date': 'DATE(solotodo_entityvisit.timestamp)'})\
            .values(*qs_values_args)\
            .annotate(
                count=Count('id'),
                normal_price_sum=Sum('entity_history__normal_price'),
                offer_price_sum=Sum('entity_history__offer_price')
            )\
            .order_by(*qs_values_args)

        result = []

        for entry in agg_result:
            subresult = {grouping: entry[conversion_dict[grouping]]
                         for grouping in groupings}
            subresult['count'] = entry['count']
            subresult['normal_price_sum'] = \
                str(Decimal(entry['normal_price_sum']))
            subresult['offer_price_sum'] = \
                str(Decimal(entry['offer_price_sum']))
            result.append(subresult)

        return result
