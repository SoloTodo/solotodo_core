from django.contrib.auth import get_user_model
from django.db.models import Q
from django_filters import rest_framework

from solotodo.filter_querysets import stores__view_store_update_logs, \
    categories_view, entities__view, stores__view_store
from solotodo.models import Entity, StoreUpdateLog, \
    Product, EntityHistory, Country


class UserFilterSet(rest_framework.FilterSet):
    @property
    def qs(self):
        parent = super(UserFilterSet, self).qs
        user = self.request.user
        if 'solotodo.view_users' in user.permissions:
            return parent
        elif 'solotodo.view_users_with_staff_actions' in user.permissions:
            return parent.filter_with_staff_actions()
        else:
            return parent.none()

    class Meta:
        model = get_user_model()
        fields = []


class StoreUpdateLogFilterSet(rest_framework.FilterSet):
    @property
    def qs(self):
        parent = super(StoreUpdateLogFilterSet, self).qs
        if self.request:
            stores_with_permission = stores__view_store_update_logs(
                self.request)
            return parent.filter(store__in=stores_with_permission)
        return parent

    class Meta:
        model = StoreUpdateLog
        fields = ('store',)


class EntityFilterSet(rest_framework.FilterSet):
    stores = rest_framework.ModelMultipleChoiceFilter(
        queryset=stores__view_store,
        name='store',
        label='Stores'
    )
    categories = rest_framework.ModelMultipleChoiceFilter(
        queryset=categories_view,
        name='category',
        label='Categories'
    )
    is_available = rest_framework.BooleanFilter(
        name='is_available', method='_is_available', label='Is available?')
    is_active = rest_framework.BooleanFilter(
        name='is_active', method='_is_active', label='Is active?')
    is_associated = rest_framework.BooleanFilter(
        name='is_associated', method='_is_associated', label='Is associated?')

    @property
    def qs(self):
        parent = super(EntityFilterSet, self).qs.select_related(
            'active_registry', 'product__instance_model')
        if self.request:
            categories_with_permission = categories_view(self.request)
            stores_with_permission = stores__view_store(self.request)

            return parent.filter(
                Q(category__in=categories_with_permission) &
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
    categories = rest_framework.ModelMultipleChoiceFilter(
        queryset=categories_view,
        name='instance_model__model__category',
        label='Categories'
    )
    availability_countries = rest_framework.ModelMultipleChoiceFilter(
        queryset=Country.objects.all(),
        label='Available in countries',
        method='_availability_countries'
    )
    availability_stores = rest_framework.ModelMultipleChoiceFilter(
        queryset=stores__view_store,
        label='Available in stores',
        method='_availability_stores'
    )
    last_updated = rest_framework.DateTimeFromToRangeFilter(
        name='last_updated'
    )
    creation_date = rest_framework.DateTimeFromToRangeFilter(
        name='creation_date'
    )
    search = rest_framework.CharFilter(
        label='Search',
        method='_search'
    )

    @property
    def qs(self):
        parent = super(ProductFilterSet, self).qs.select_related(
            'instance_model')
        if self.request:
            categories_with_permission = categories_view(self.request)

            parent = parent.filter_by_category(categories_with_permission)
        return parent.select_related('instance_model__model__category')

    def _availability_countries(self, queryset, name, value):
        if value:
            return queryset.filter_by_availability_in_countries(value)
        return queryset

    def _availability_stores(self, queryset, name, value):
        if value:
            return queryset.filter_by_availability_in_stores(value)
        return queryset

    def _search(self, queryset, name, value):
        if value:
            return queryset.filter_by_keywords(value)
        return queryset

    class Meta:
        model = Product
        fields = []


class EntityHistoryFilterSet(rest_framework.FilterSet):
    timestamp = rest_framework.DateTimeFromToRangeFilter(
        name='timestamp'
    )
    available_only = rest_framework.BooleanFilter(
        method='_available_only',
        label='Available only?'
    )
    entities = rest_framework.ModelMultipleChoiceFilter(
        queryset=entities__view,
        name='entity',
        label='Entities'
    )

    @property
    def qs(self):
        parent = super(EntityHistoryFilterSet, self).qs.select_related()
        if self.request:
            categories_with_permission = categories_view(self.request)
            stores_with_permission = stores__view_store(self.request)

            return parent.filter(
                Q(entity__category__in=categories_with_permission) &
                Q(entity__store__in=stores_with_permission))
        return parent

    def _available_only(self, queryset, name, value):
        if value:
            return queryset.get_available()
        return queryset

    class Meta:
        model = EntityHistory
        fields = []
