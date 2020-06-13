from django_filters import rest_framework

from solotodo.custom_model_multiple_choice_filter import \
    CustomModelMultipleChoiceFilter
from.models import KeywordSearch, KeywordSearchUpdate


class KeywordSearchUpdateFilterSet(rest_framework.FilterSet):
    searches = CustomModelMultipleChoiceFilter(
        queryset=KeywordSearch.objects.all(),
        field_name='search',
        label='Searches')

    class Meta:
        model = KeywordSearchUpdate
        fields = ['searches']
