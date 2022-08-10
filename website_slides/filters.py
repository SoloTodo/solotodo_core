from django_filters import rest_framework

from solotodo.custom_model_multiple_choice_filter import \
    CustomModelMultipleChoiceFilter
from solotodo.filter_querysets import create_category_filter


class WebsiteSlideFilterSet(rest_framework.FilterSet):
    categories = CustomModelMultipleChoiceFilter(
        queryset=create_category_filter(),
        field_name='categories',
        label='Categories'
    )
    only_active_category = rest_framework.BooleanFilter(
        field_name='only_active_category',
        method='_only_active_category',
        label='Is active for category pages?')
    only_active_home = rest_framework.BooleanFilter(
        field_name='only_active_home',
        method='_only_active_home',
        label='Is active for homepage?')

    def _only_active_category(self, queryset, name, value):
        if value:
            return queryset.filter(category_priority__isnull=False)
        return queryset


    def _only_active_home(self, queryset, name, value):
        if value:
            return queryset.filter(home_priority__isnull=False)
        return queryset