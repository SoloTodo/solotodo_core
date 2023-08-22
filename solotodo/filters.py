from django.contrib.auth import get_user_model
from django.db.models import F, Q
from django_filters import rest_framework, IsoDateTimeFromToRangeFilter

from solotodo.custom_model_multiple_choice_filter import \
    CustomModelMultipleChoiceFilter
from solotodo.filter_querysets import create_store_filter, \
    create_category_filter, create_product_filter, create_entity_filter, \
    create_website_filter
from solotodo.models import Entity, StoreUpdateLog, \
    Product, EntityHistory, Country, Store, StoreType, Lead, Website, \
    Visit, Rating, ProductPicture, \
    Brand, StoreSection, EntitySectionPosition


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
    ids = CustomModelMultipleChoiceFilter(
        queryset=create_store_filter(),
        method='_ids',
        label='Stores'
    )
    countries = rest_framework.ModelMultipleChoiceFilter(
        queryset=Country.objects.all(),
        field_name='country',
        label='Countries'
    )
    types = rest_framework.ModelMultipleChoiceFilter(
        queryset=StoreType.objects.all(),
        field_name='type',
        label='Types'
    )

    @property
    def qs(self):
        qs = super(StoreFilterSet, self).qs

        if self.request:
            qs = qs.filter_by_user_perms(self.request.user, 'view_store')

        return qs

    def _ids(self, queryset, name, value):
        if value:
            return queryset & value
        return queryset

    class Meta:
        model = Store
        fields = []


class StoreUpdateLogFilterSet(rest_framework.FilterSet):
    @property
    def qs(self):
        qs = super(StoreUpdateLogFilterSet, self).qs

        if self.request:
            stores_with_permission = Store.objects.filter_by_user_perms(
                self.request.user, 'view_store_update_logs')
            qs = qs.filter(store__in=stores_with_permission)
        return qs

    class Meta:
        model = StoreUpdateLog
        fields = ('store',)


class EntityFilterSet(rest_framework.FilterSet):
    ids = CustomModelMultipleChoiceFilter(
        queryset=create_entity_filter(),
        method='_ids',
        label='Entities'
    )
    stores = CustomModelMultipleChoiceFilter(
        queryset=create_store_filter(),
        field_name='store',
        label='Stores'
    )
    products = CustomModelMultipleChoiceFilter(
        queryset=create_product_filter(),
        field_name='product',
        label='Products'
    )
    categories = CustomModelMultipleChoiceFilter(
        queryset=create_category_filter(),
        field_name='category',
        label='Categories'
    )
    countries = rest_framework.ModelMultipleChoiceFilter(
        queryset=Country.objects.all(),
        field_name='store__country',
        label='Countries'
    )
    store_types = rest_framework.ModelMultipleChoiceFilter(
        queryset=StoreType.objects.all(),
        field_name='store__type',
        label='Store types'
    )
    db_brands = rest_framework.ModelMultipleChoiceFilter(
        queryset=Brand.objects.all(),
        field_name='product__brand',
        label='Brands'
    )
    exclude_refurbished = rest_framework.BooleanFilter(
        field_name='exclude_refurbished',
        method='_exclude_refurbished',
        label='Exclude refurbished?'
    )
    sku = rest_framework.CharFilter(
        lookup_expr='icontains'
    )
    exclude_marketplace = rest_framework.BooleanFilter(
        field_name='exclude_marketplace',
        method='_exclude_marketplace',
        label='Exclude marketplace?'
    )
    is_marketplace = rest_framework.BooleanFilter(
        field_name='is_marketplace',
        method='_is_marketplace',
        label='Is from marketplace?'
    )
    exclude_with_monthly_payment = rest_framework.BooleanFilter(
        field_name='exclude_with_monthly_payment',
        method='_exclude_with_monthly_payment',
        label='Exclude with cell monthly payment?'
    )

    is_available = rest_framework.BooleanFilter(
        field_name='is_available', method='_is_available',
        label='Is available?')
    is_active = rest_framework.BooleanFilter(
        field_name='is_active', method='_is_active', label='Is active?')
    is_associated = rest_framework.BooleanFilter(
        field_name='is_associated', method='_is_associated',
        label='Is associated?')

    @property
    def qs(self):
        qs = super(EntityFilterSet, self).qs.select_related(
            'product__instance_model',
            'cell_plan__instance_model'
        ).prefetch_related('active_registry')

        if self.request:
            qs = qs.filter_by_user_perms(self.request.user, 'view_entity')

        return qs

    def _ids(self, queryset, name, value):
        if value:
            return queryset & value
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

    def _exclude_refurbished(self, queryset, name, value):
        if value:
            return queryset.filter(condition='https://schema.org/NewCondition')
        else:
            return queryset

    def _exclude_marketplace(self, queryset, name, value):
        if value:
            return queryset.filter(seller__isnull=True)
        else:
            return queryset


    def _is_marketplace(self, queryset, name, value):
        if value:
            return queryset.filter(seller__isnull=False)
        elif value is False:
            return queryset.filter(seller__isnull=True)
        else:
            return queryset

    def _exclude_with_monthly_payment(self, queryset, name, value):
        if value:
            return queryset.filter(
                active_registry__cell_monthly_payment__isnull=True)
        else:
            return queryset

    class Meta:
        model = Entity
        fields = ['is_visible', ]


class CategoryFullBrowseEntityFilterSet(EntityFilterSet):
    normal_price_usd = rest_framework.RangeFilter(
        label='Normal price (USD)',
        field_name='normal_price_usd'
    )
    offer_price_usd = rest_framework.RangeFilter(
        label='Offer price (USD)',
        field_name='offer_price_usd'
    )

    @classmethod
    def get_entities(cls, request, category):
        entities = Entity.objects.get_available().filter(
            active_registry__cell_monthly_payment__isnull=True,
            product__instance_model__model__category=category
        ).annotate(
            normal_price_usd=F('active_registry__normal_price') /
            F('currency__exchange_rate'),
            offer_price_usd=F('active_registry__offer_price') /
            F('currency__exchange_rate')
        ).select_related(
            'category',
            'currency',
            'active_registry',
            'cell_plan__instance_model__model__category',
            'product__instance_model__model__category',
            'store'
        )

        filterset = cls(
            data=request.query_params,
            request=request,
            queryset=entities
        )

        if 'products' in request.query_params:
            filterset.form.fields['products'].queryset = \
                create_product_filter()(request)

        if 'categories' in request.query_params:
            filterset.form.fields['categories'].queryset = \
                create_category_filter()(request)

        if 'stores' in request.query_params:
            filterset.form.fields['stores'].queryset = \
                create_store_filter()(request)

        return filterset.qs.order_by('product', 'cell_plan', 'offer_price_usd')

    class Meta:
        model = Entity
        fields = []


class EntityEstimatedSalesFilterSet(rest_framework.FilterSet):
    stores = CustomModelMultipleChoiceFilter(
        queryset=create_store_filter('view_store_stocks'),
        field_name='store',
        label='Stores'
    )
    categories = CustomModelMultipleChoiceFilter(
        queryset=create_category_filter(),
        field_name='category',
        label='Categories'
    )
    ids = CustomModelMultipleChoiceFilter(
        queryset=create_entity_filter('view_entity_stocks'),
        method='_ids',
        label='Entities'
    )

    def _ids(self, queryset, name, value):
        if value:
            return queryset & value
        return queryset

    @property
    def qs(self):
        qs = super(EntityEstimatedSalesFilterSet, self).qs.select_related(
            'product__instance_model',
            'cell_plan'
        ).prefetch_related('active_registry')
        if self.request:
            qs = qs.filter_by_user_perms(
                self.request.user, 'view_entity_stocks')
        return qs


class EntityStaffFilterSet(rest_framework.FilterSet):
    stores = CustomModelMultipleChoiceFilter(
        queryset=create_store_filter(),
        field_name='store',
        label='Stores'
    )
    categories = CustomModelMultipleChoiceFilter(
        queryset=create_category_filter('is_category_staff'),
        field_name='category',
        label='Categories'
    )
    countries = rest_framework.ModelMultipleChoiceFilter(
        queryset=Country.objects.all(),
        field_name='store__country',
        label='Countries'
    )

    @property
    def qs(self):
        qs = super(EntityStaffFilterSet, self).qs.select_related(
            'product__instance_model',
            'cell_plan__instance_model'
        ).prefetch_related('active_registry')

        if self.request:
            qs = qs.filter_by_user_perms(
                self.request.user, 'is_entity_staff')
        return qs


class ProductFilterSet(rest_framework.FilterSet):
    ids = CustomModelMultipleChoiceFilter(
        queryset=create_product_filter(),
        method='_ids',
        label='Products'
    )
    categories = CustomModelMultipleChoiceFilter(
        queryset=create_category_filter(),
        field_name='instance_model__model__category',
        label='Categories'
    )
    availability_countries = CustomModelMultipleChoiceFilter(
        queryset=Country.objects.all(),
        label='Available in countries',
        method='_availability_countries'
    )
    availability_stores = CustomModelMultipleChoiceFilter(
        queryset=create_store_filter(),
        label='Available in stores',
        method='_availability_stores'
    )
    exclude_marketplace = rest_framework.BooleanFilter(
        label='Exclude marketplace',
        method='_exclude_marketplace'
    )
    exclude_refurbished = rest_framework.BooleanFilter(
        label='Exclude refurbished',
        method='_exclude_refurbished'
    )
    brands = CustomModelMultipleChoiceFilter(
        queryset=Brand.objects.all(),
        field_name='brand',
        label='Brands'
    )
    last_updated = IsoDateTimeFromToRangeFilter(
        field_name='last_updated'
    )
    creation_date = IsoDateTimeFromToRangeFilter(
        field_name='creation_date'
    )
    search = rest_framework.CharFilter(
        label='Search',
        method='_search'
    )
    name = rest_framework.CharFilter(
        label='Name',
        method='_name'
    )
    part_number = rest_framework.CharFilter(
        label='Part number',
        method='_part_number'
    )

    @property
    def qs(self):
        self.entities_filter = Q()

        qs = super(ProductFilterSet, self).qs.select_related(
            'instance_model__model__category')

        if self.request:
            qs = qs.filter_by_user_perms(self.request.user, 'view_product')

        if self.entities_filter:
            entities_query = Entity.objects.get_available().filter(
                self.entities_filter)
            qs = qs.filter(entity__in=entities_query).distinct()

        return qs

    def _ids(self, queryset, name, value):
        if value:
            return queryset & value
        return queryset

    def _exclude_marketplace(self, queryset, name, value):
        if value:
            self.entities_filter &= Q(seller__isnull=True)
        return queryset

    def _exclude_refurbished(self, queryset, name, value):
        if value:
            self.entities_filter &= Q(condition='https://schema.org/NewCondition')
        return queryset

    def _availability_countries(self, queryset, name, value):
        if value:
            self.entities_filter &= Q(store__country__in=value)
        return queryset

    def _availability_stores(self, queryset, name, value):
        if value:
            self.entities_filter &= Q(store__in=value)
        return queryset

    def _search(self, queryset, name, value):
        if value:
            return queryset.filter_by_search_string(value)
        return queryset

    def _name(self, queryset, name, value):
        if value:
            return queryset.filter_by_name(value)
        return queryset

    def _part_number(self, queryset, name, value):
        if value:
            return queryset.filter(part_number__icontains=value)
        return queryset

    class Meta:
        model = Product
        fields = []


class EntityHistoryFilterSet(rest_framework.FilterSet):
    timestamp = IsoDateTimeFromToRangeFilter(
        field_name='timestamp'
    )
    stores = CustomModelMultipleChoiceFilter(
        queryset=create_store_filter(),
        field_name='entity__store',
        label='Stores'
    )
    countries = rest_framework.ModelMultipleChoiceFilter(
        queryset=Country.objects.all(),
        field_name='entity__store__country',
        label='Countries'
    )
    exclude_unavailable = rest_framework.BooleanFilter(
        field_name='exclude_unavailable', method='_exclude_unavailable',
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
        field_name='timestamp'
    )
    stores = CustomModelMultipleChoiceFilter(
        queryset=create_store_filter('view_store_leads'),
        field_name='entity_history__entity__store',
        label='Stores'
    )
    products = CustomModelMultipleChoiceFilter(
        queryset=create_product_filter(),
        field_name='entity_history__entity__product',
        label='Products'
    )
    websites = CustomModelMultipleChoiceFilter(
        queryset=create_website_filter(),
        field_name='website',
        label='Websites'
    )
    categories = CustomModelMultipleChoiceFilter(
        queryset=create_category_filter('view_category_leads'),
        field_name='entity_history__entity__category',
        label='Categories'
    )
    countries = rest_framework.ModelMultipleChoiceFilter(
        queryset=Country.objects.all(),
        field_name='entity_history__entity__store__country',
        label='Countries'
    )
    entities = CustomModelMultipleChoiceFilter(
        queryset=create_entity_filter(),
        field_name='entity_history__entity',
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
        field_name='timestamp'
    )
    products = CustomModelMultipleChoiceFilter(
        queryset=create_product_filter(),
        field_name='product',
        label='Products'
    )
    websites = CustomModelMultipleChoiceFilter(
        queryset=create_website_filter('view_website_visits'),
        field_name='website',
        label='Websites'
    )
    categories = CustomModelMultipleChoiceFilter(
        queryset=create_category_filter('view_category_visits'),
        field_name='product__instance_model__model__category',
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


class RatingFilterSet(rest_framework.FilterSet):
    stores = CustomModelMultipleChoiceFilter(
        queryset=create_store_filter(),
        field_name='store',
        label='Stores'
    )
    products = CustomModelMultipleChoiceFilter(
        queryset=create_product_filter(),
        field_name='product',
        label='Products'
    )
    categories = CustomModelMultipleChoiceFilter(
        queryset=create_category_filter(),
        field_name='product__instance_model__model__category',
        label='Categories'
    )
    pending_only = rest_framework.BooleanFilter(
        method='_pending_only'
    )
    with_product_rating_only = rest_framework.BooleanFilter(
        method='_with_product_rating_only'
    )

    @property
    def qs(self):
        qs = super(RatingFilterSet, self).qs.select_related(
            'store',
            'product__instance_model',
            'user'
        )

        if self.request:
            if not self.request.user.has_perm('solotodo.is_ratings_staff'):
                qs = qs.filter(status=Rating.RATING_APPROVED)
            qs = qs.filter_by_user_perms(self.request.user, 'view_rating')

        return qs

    def _pending_only(self, queryset, name, value):
        if value:
            queryset = queryset.filter(status=Rating.RATING_PENDING)
        return queryset

    def _with_product_rating_only(self, queryset, name, value):
        if value:
            queryset = queryset.filter(product_rating__isnull=False)
        return queryset

    class Meta:
        model = Rating
        fields = []


class ProductPictureFilterSet(rest_framework.FilterSet):
    products = CustomModelMultipleChoiceFilter(
        queryset=create_product_filter(),
        field_name='product',
        label='Products'
    )

    @property
    def qs(self):
        qs = super(ProductPictureFilterSet, self).qs.select_related(
            'product__instance_model__model__category'
        )

        if self.request:
            qs = qs.filter_by_user_perms(self.request.user,
                                         'view_product_picture')
        return qs

    class Meta:
        model = ProductPicture
        fields = []


class EntitySectionPositionFilterSet(rest_framework.FilterSet):
    entities = CustomModelMultipleChoiceFilter(
        queryset=create_entity_filter(),
        field_name='entity_history__entity',
        label='Entities'
    )

    is_active = rest_framework.BooleanFilter(
        field_name='is_active', method='_is_active', label='Is active?')

    timestamp = IsoDateTimeFromToRangeFilter(
        field_name='entity_history__timestamp'
    )

    @property
    def qs(self):
        qs = super(EntitySectionPositionFilterSet, self).qs

        if self.request:
            qs = qs.filter_by_user_perms(
                self.request.user, 'view_entity_positions')\
                .select_related('entity_history', 'section')

        return qs

    def _is_active(self, queryset, name, value):
        if value:
            return queryset.get_active()
        else:
            return queryset.get_inactive()

    class Meta:
        model = EntitySectionPosition
        fields = []


class StoreSectionFilterSet(rest_framework.FilterSet):
    @property
    def qs(self):
        qs = super(StoreSectionFilterSet, self).qs

        if self.request:
            qs = qs.filter_by_user_perms(self.request.user,
                                         'view_store_section')

        return qs

    class Meta:
        model = StoreSection
        fields = []
