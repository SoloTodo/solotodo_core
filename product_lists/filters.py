from django_filters import rest_framework

from solotodo.custom_model_multiple_choice_filter import \
    CustomModelMultipleChoiceFilter
from solotodo.filter_querysets import create_category_filter
from .models import ProductList


class ProductListFilterSet(rest_framework.FilterSet):
    categories = CustomModelMultipleChoiceFilter(
        queryset=create_category_filter(),
        name='category',
        label='Category'
    )

    class Meta:
        model = ProductList
        fields = ()
