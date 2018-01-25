from django.contrib.auth import get_user_model
from django.db.models import Q, F
from django_filters import rest_framework

from solotodo.filter_querysets import create_store_filter, \
    create_category_filter, create_product_filter, create_entity_filter, \
    create_website_filter
from solotodo.filter_utils import IsoDateTimeFromToRangeFilter
from solotodo.models import Entity, StoreUpdateLog, \
    Product, EntityHistory, Country, Store, StoreType, Lead, Website, \
    Currency, Visit


class UserFilterSet(rest_framework.FilterSet):
    @property
    def qs(self):
        parent = super(UserFilterSet, self).qs
        user = self.request.user
        if not user.is_authenticated:
            return parent.none()
        if 'solotodo.view_users' in user.permissions:
            return parent
        elif 'solotodo.view_users_with_staff_actions' in user.permissions:
            return parent.filter_with_staff_actions()
        else:
            return parent.none()

    class Meta:
        model = get_user_model()
        fields = []


class WebsiteFilterSet(rest_framework.FilterSet):
    @property
    def qs(self):
        qs = super(WebsiteFilterSet, self).qs
        if self.request:
            qs = qs.filter_by_user_perms(self.request.user, 'view_website')
        return qs

    class Meta:
        model = Website
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
    ids = rest_framework.ModelMultipleChoiceFilter(
        queryset=Entity.objects.all(),
        method='_ids',
        label='Entities'
    )
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
            'active_registry',
            'product__instance_model',
            'cell_plan'
        )
        categories_with_permission = create_category_filter()(self.request)
        stores_with_permission = create_store_filter()(self.request)

        return qs.filter(
            Q(category__in=categories_with_permission) &
            Q(store__in=stores_with_permission))

    def _ids(self, queryset, name, value):
        if value:
            return queryset.filter(pk__in=[x.pk for x in value])
        return queryset

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


class EntityEstimatedSalesFilterSet(rest_framework.FilterSet):
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
        qs = super(EntityEstimatedSalesFilterSet, self).qs.select_related(
            'active_registry',
            'product__instance_model',
            'cell_plan'
        )
        if self.request:
            qs = qs.filter_by_user_perms(
                self.request.user, 'view_entity_stocks')
        return qs


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
        qs = super(EntityStaffFilterSet, self).qs.select_related(
            'active_registry',
            'product__instance_model',
            'cell_plan'
        )
        if self.request:
            qs = qs.filter_by_user_perms(
                self.request.user, 'is_entity_staff')
        return qs


class ProductsBrowseEntityFilterSet(rest_framework.FilterSet):
    products = rest_framework.ModelMultipleChoiceFilter(
        queryset=Product.objects.all(),
        name='product',
        label='Products'
    )
    categories = rest_framework.ModelMultipleChoiceFilter(
        queryset=create_category_filter(),
        name='category',
        label='Categories'
    )
    stores = rest_framework.ModelMultipleChoiceFilter(
        queryset=create_store_filter(),
        name='store',
        label='Stores'
    )
    countries = rest_framework.ModelMultipleChoiceFilter(
        queryset=Country.objects.all(),
        name='store__country',
        label='Countries'
    )
    currencies = rest_framework.ModelMultipleChoiceFilter(
        queryset=Currency.objects.all(),
        name='currency',
        label='Currencies'
    )
    store_types = rest_framework.ModelMultipleChoiceFilter(
        queryset=StoreType.objects.all(),
        name='store__type',
        label='Store types'
    )
    normal_price = rest_framework.RangeFilter(
        label='Normal price',
        name='active_registry__normal_price'
    )
    offer_price = rest_framework.RangeFilter(
        label='Offer price',
        name='active_registry__offer_price'
    )
    normal_price_usd = rest_framework.RangeFilter(
        label='Normal price (USD)',
        name='normal_price_usd'
    )
    offer_price_usd = rest_framework.RangeFilter(
        label='Offer price (USD)',
        name='offer_price_usd'
    )

    @classmethod
    def create(cls, request):
        entities = Entity.objects.annotate(
            offer_price_usd=F('active_registry__offer_price') /
            F('currency__exchange_rate'),
            normal_price_usd=F('active_registry__normal_price') /
            F('currency__exchange_rate')
        )
        return cls(
            data=request.query_params, queryset=entities, request=request)

    @property
    def qs(self):
        qs = super(ProductsBrowseEntityFilterSet, self).qs.get_available() \
            .filter(active_registry__cell_monthly_payment__isnull=True) \
            .filter(product__isnull=False) \
            .select_related(
            'active_registry',
            'product__instance_model__model__category',
        )
        stores_with_permission = create_store_filter()(self.request)

        return qs.filter(store__in=stores_with_permission)

    class Meta:
        model = Entity
        fields = []


class ProductFilterSet(rest_framework.FilterSet):
    ids = rest_framework.ModelMultipleChoiceFilter(
        queryset=Product.objects.all(),
        method='_ids',
        label='Products'
    )
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

    def _ids(self, queryset, name, value):
        if value:
            return queryset.filter(pk__in=[x.pk for x in value])
        return queryset

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
            return queryset.filter_by_search_string(value)
        return queryset

    class Meta:
        model = Product
        fields = []


class EntityHistoryFilterSet(rest_framework.FilterSet):
    timestamp = IsoDateTimeFromToRangeFilter(
        name='timestamp'
    )
    stores = rest_framework.ModelMultipleChoiceFilter(
        queryset=create_store_filter(),
        name='entity__store',
        label='Stores'
    )
    countries = rest_framework.ModelMultipleChoiceFilter(
        queryset=Country.objects.all(),
        name='entity__store__country',
        label='Countries'
    )
    exclude_unavailable = rest_framework.BooleanFilter(
        name='exclude_unavailable', method='_exclude_unavailable',
        label='Exclude unavailable?')

    @property
    def qs(self):
        qs = super(EntityHistoryFilterSet, self).qs.select_related(
            'entity__store',
            'entity__category',
        )
        if self.request:
            qs = qs.filter_by_user_perms(self.request.user,
                                         'view_entity_history')

        return qs

    def _exclude_unavailable(self, queryset, name, value):
        if value:
            return queryset.get_available()

        return queryset

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
    websites = rest_framework.ModelMultipleChoiceFilter(
        queryset=Website.objects.all(),
        name='website',
        label='Websites'
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
        qs = super(LeadFilterSet, self).qs.select_related(
            'entity_history__entity__product__instance_model__model__category',
            'user'
        )
        if self.request:
            qs = qs.filter_by_user_perms(self.request.user, 'view_lead')
        return qs

    class Meta:
        model = Lead
        fields = []


class VisitFilterSet(rest_framework.FilterSet):
    timestamp = IsoDateTimeFromToRangeFilter(
        name='timestamp'
    )
    products = rest_framework.ModelMultipleChoiceFilter(
        queryset=create_product_filter(),
        name='product',
        label='Products'
    )
    websites = rest_framework.ModelMultipleChoiceFilter(
        queryset=create_website_filter('view_website_visits'),
        name='website',
        label='Websites'
    )
    categories = rest_framework.ModelMultipleChoiceFilter(
        queryset=create_category_filter('view_category_visits'),
        name='product__instance_model__model__category',
        label='Categories'
    )

    @property
    def qs(self):
        qs = super(VisitFilterSet, self).qs.select_related(
            'product__instance_model__model__category',
            'user'
        )
        if self.request:
            qs = qs.filter_by_user_perms(self.request.user, 'view_visit')
        return qs

    class Meta:
        model = Visit
        fields = []
