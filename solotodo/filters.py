from django.db.models import Q
from django_filters import rest_framework
import django_filters
from guardian.shortcuts import get_objects_for_user

from solotodo.models import Entity, StoreUpdateLog, Store, ProductType


class StoreUpdateLogFilterSet(rest_framework.FilterSet):
    @property
    def qs(self):
        parent = super(StoreUpdateLogFilterSet, self).qs
        if self.request:
            stores = get_objects_for_user(
                self.request.user, 'view_store_update_logs', klass=Store)
            return parent.filter(store__in=stores)
        return parent

    class Meta:
        model = StoreUpdateLog
        fields = ('store',)


def stores(request):
    if request:
        return get_objects_for_user(
            request.user, 'view_store_entities', Store)
    return Store.objects.all()


def product_types(request):
    if request:
        return get_objects_for_user(
            request.user, 'view_product_type_entities', ProductType)
    return ProductType.objects.all()


class EntityFilterSet(rest_framework.FilterSet):
    stores = django_filters.ModelMultipleChoiceFilter(
        queryset=stores,
        name='store'
    )
    product_types = django_filters.ModelMultipleChoiceFilter(
        queryset=product_types,
        name='product_type'
    )
    is_available = django_filters.BooleanFilter(
        name='is_available', method='_is_available', label='Is available?')

    @property
    def qs(self):
        parent = super(EntityFilterSet, self).qs
        if self.request:
            product_types_with_permission = get_objects_for_user(
                self.request.user, 'view_product_type_entities', ProductType)
            stores_with_permission = get_objects_for_user(
                self.request.user, 'view_store_entities', Store)

            return parent.filter(
                Q(product_type__in=product_types_with_permission) &
                Q(store__in=stores_with_permission))
        return parent

    def _is_available(self, queryset, name, value):
        if value:
            return queryset.get_available()
        else:
            return queryset.get_unavailable()

    class Meta:
        model = Entity
        fields = []
