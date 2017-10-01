from django.contrib.auth import get_user_model
from django.db.models import Q
from django_filters import rest_framework

from solotodo.filter_querysets import create_store_filter, \
    create_category_filter, create_product_filter, create_entity_filter
from solotodo.filter_utils import IsoDateTimeFromToRangeFilter
from solotodo.models import Entity, StoreUpdateLog, \
    Product, EntityHistory, Country, Store, StoreType, Lead, ApiClient
from solotodo.serializers import EntityWithInlineProductSerializer


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


class StoreFilterSet(rest_framework.FilterSet):
    countries = rest_framework.ModelMultipleChoiceFilter(
        queryset=Country.objects.all(),
        name='country',
        label='Countries'
    )
    types = rest_framework.ModelMultipleChoiceFilter(
        queryset=StoreType.objects.all(),
        name='type',
        label='Types'
    )

    @property
    def qs(self):
        qs = super(StoreFilterSet, self).qs
        return create_store_filter(qs=qs)(self.request)

    class Meta:
        model = Store
        fields = ['is_active']


class StoreUpdateLogFilterSet(rest_framework.FilterSet):
    @property
    def qs(self):
        qs = super(StoreUpdateLogFilterSet, self).qs
        stores_with_permission = create_store_filter(
            'view_store_update_logs')(self.request)
        qs = qs.filter(store__in=stores_with_permission)
        return qs

    class Meta:
        model = StoreUpdateLog
        fields = ('store',)


class EntityFilterSet(rest_framework.FilterSet):
    stores = rest_framework.ModelMultipleChoiceFilter(
        queryset=create_store_filter(),
        name='store',
        label='Stores'
    )
    categories = rest_framework.ModelMultipleChoiceFilter(
        queryset=create_category_filter(),
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
        qs = super(EntityFilterSet, self).qs.select_related(
            'active_registry', 'product__instance_model')
        categories_with_permission = create_category_filter()(self.request)
        stores_with_permission = create_store_filter()(self.request)

        return qs.filter(
            Q(category__in=categories_with_permission) &
            Q(store__in=stores_with_permission))

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


class EntitySalesFilterSet(rest_framework.FilterSet):
    stores = rest_framework.ModelMultipleChoiceFilter(
        queryset=create_store_filter('view_store_stocks'),
        name='store',
        label='Stores'
    )
    categories = rest_framework.ModelMultipleChoiceFilter(
        queryset=create_category_filter('view_category_stocks'),
        name='category',
        label='Categories'
    )

    @property
    def qs(self):
        qs = super(EntitySalesFilterSet, self).qs.select_related(
            'active_registry', 'product__instance_model')
        if self.request:
            qs = qs.filter_by_user_perms(
                self.request.user, 'view_entity_stocks')
        return qs

    def estimated_sales(self, request, start_date, end_date, limit):
        result = self.qs.estimated_sales(start_date, end_date)

        if limit:
            result = result[:limit]

        entity_serializer = EntityWithInlineProductSerializer(
            [e['entity'] for e in result],
            many=True, context={'request': request})
        entity_serialization_dict = {
            e['id']: e for e in entity_serializer.data}

        return [
            {
                'entity': entity_serialization_dict[entry['entity'].id],
                'stock': entry['stock'],
                'normal_price': entry['normal_price'],
                'offer_price': entry['offer_price'],
            }
            for entry in result
        ]


class EntityStaffFilterSet(rest_framework.FilterSet):
    stores = rest_framework.ModelMultipleChoiceFilter(
        queryset=create_store_filter('is_store_staff'),
        name='store',
        label='Stores'
    )
    categories = rest_framework.ModelMultipleChoiceFilter(
        queryset=create_category_filter('is_category_staff'),
        name='category',
        label='Categories'
    )

    @property
    def qs(self):
        qs = super(EntityStaffFilterSet, self).qs
        if self.request:
            qs = qs.filter_by_user_perms(
                self.request.user, 'is_entity_staff')
        return qs


class ProductFilterSet(rest_framework.FilterSet):
    categories = rest_framework.ModelMultipleChoiceFilter(
        queryset=create_category_filter(),
        name='instance_model__model__category',
        label='Categories'
    )
    availability_countries = rest_framework.ModelMultipleChoiceFilter(
        queryset=Country.objects.all(),
        label='Available in countries',
        method='_availability_countries'
    )
    availability_stores = rest_framework.ModelMultipleChoiceFilter(
        queryset=create_store_filter(),
        label='Available in stores',
        method='_availability_stores'
    )
    last_updated = IsoDateTimeFromToRangeFilter(
        name='last_updated'
    )
    creation_date = IsoDateTimeFromToRangeFilter(
        name='creation_date'
    )
    search = rest_framework.CharFilter(
        label='Search',
        method='_search'
    )

    @property
    def qs(self):
        qs = super(ProductFilterSet, self).qs.select_related(
            'instance_model')
        categories_with_permission = create_category_filter()(self.request)
        qs = qs.filter_by_category(categories_with_permission)
        return qs.select_related('instance_model__model__category')

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
    timestamp = IsoDateTimeFromToRangeFilter(
        name='timestamp'
    )

    @property
    def qs(self):
        qs = super(EntityHistoryFilterSet, self).qs.select_related()
        categories_with_permission = create_category_filter()(self.request)
        stores_with_permission = create_store_filter()(self.request)

        return qs.filter(
            Q(entity__category__in=categories_with_permission) &
            Q(entity__store__in=stores_with_permission))

    class Meta:
        model = EntityHistory
        fields = []


class LeadFilterSet(rest_framework.FilterSet):
    timestamp = IsoDateTimeFromToRangeFilter(
        name='timestamp'
    )
    stores = rest_framework.ModelMultipleChoiceFilter(
        queryset=create_store_filter('view_store_leads'),
        name='entity_history__entity__store',
        label='Stores'
    )
    products = rest_framework.ModelMultipleChoiceFilter(
        queryset=create_product_filter(),
        name='entity_history__entity__product',
        label='Products'
    )
    api_clients = rest_framework.ModelMultipleChoiceFilter(
        queryset=ApiClient.objects.all(),
        name='api_client',
        label='API Clients'
    )
    categories = rest_framework.ModelMultipleChoiceFilter(
        queryset=create_category_filter('view_category_leads'),
        name='entity_history__entity__category',
        label='Categories'
    )
    countries = rest_framework.ModelMultipleChoiceFilter(
        queryset=Country.objects.all(),
        name='entity_history__entity__store__country',
        label='Countries'
    )
    entities = rest_framework.ModelMultipleChoiceFilter(
        queryset=create_entity_filter(),
        name='entity_history__entity',
        label='Entities'
    )

    @property
    def qs(self):
        qs = super(LeadFilterSet, self).qs.select_related()
        if self.request:
            qs = qs.filter_by_user_perms(self.request.user, 'view_lead')
        return qs

    class Meta:
        model = Lead
        fields = []
