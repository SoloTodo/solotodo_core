from django.db.models import Q
from django_filters import rest_framework
from guardian.shortcuts import get_objects_for_user

from solotodo.models import Entity, StoreUpdateLog, Store, ProductType, Product


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
    stores = rest_framework.ModelMultipleChoiceFilter(
        queryset=stores,
        name='store'
    )
    product_types = rest_framework.ModelMultipleChoiceFilter(
        queryset=product_types,
        name='product_type'
    )
    is_available = rest_framework.BooleanFilter(
        name='is_available', method='_is_available', label='Is available?')
    is_active = rest_framework.BooleanFilter(
        name='is_active', method='_is_active', label='Is active?')
    is_associated = rest_framework.BooleanFilter(
        name='is_associated', method='_is_associated', label='Is associated?')

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

    def _is_active(self, queryset, name, value):
        if value:
            return queryset.get_active()
        else:
            return queryset.get_inactive()

    def _is_associated(self, queryset, name, value):
        return queryset.filter(product__isnull=not value)

    class Meta:
        model = Entity
        fields = ['is_visible', ]


class ProductFilterSet(rest_framework.FilterSet):
    @property
    def qs(self):
        parent = super(ProductFilterSet, self).qs
        if self.request:
            product_types_with_permission = get_objects_for_user(
                self.request.user, 'view_product_type_products', ProductType)

            return parent.filter_product_type(product_types_with_permission)
        return parent

    class Meta:
        model = Product
        fields = []
