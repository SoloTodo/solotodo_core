from django.db.models import Q
from rest_framework.filters import FilterSet
import django_filters

from solotodo.models import Entity


class EntityFilter(FilterSet):
    is_available = django_filters.BooleanFilter(name='is_available', method='_is_available')

    def _is_available(self, queryset, name, value):
        if value:
            return queryset.get_available()
        else:
            return queryset.get_unavailable()

    class Meta:
        model = Entity
        fields = ['store', 'product_type', 'scraped_product_type']
