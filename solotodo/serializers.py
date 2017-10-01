from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.reverse import reverse

from solotodo.models import Language, Store, Currency, Country, StoreType, \
    Category, StoreUpdateLog, Entity, EntityHistory, Product, NumberFormat, \
    EntityState, Lead, ApiClient


class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ('url', 'id', 'email', 'first_name', 'last_name',
                  'date_joined',)


class ApiClientSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = ApiClient
        fields = ('url', 'id', 'name', 'url')


class MyUserSerializer(serializers.HyperlinkedModelSerializer):
    detail_url = serializers.HyperlinkedRelatedField(
        view_name='solotodouser-detail', read_only=True, source='pk')

    class Meta:
        model = get_user_model()
        fields = ('url', 'id', 'detail_url', 'email', 'first_name',
                  'last_name', 'preferred_language', 'preferred_country',
                  'preferred_currency', 'preferred_number_format',
                  'preferred_store', 'date_joined', 'permissions')
        read_only_fields = ('email', 'first_name', 'last_name',
                            'permissions')


class StoreTypeSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = StoreType
        fields = ('url', 'id', 'name')


class LanguageSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Language
        fields = ('url', 'code', 'name')


class NumberFormatSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = NumberFormat
        fields = ('url', 'name', 'thousands_separator', 'decimal_separator')


class CurrencySerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Currency
        fields = ('url', 'id', 'name', 'iso_code', 'decimal_places', 'prefix',
                  'exchange_rate', 'exchange_rate_last_updated')


class CountrySerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Country
        fields = ('url', 'id', 'name', 'currency', 'number_format')


class StoreSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Store
        fields = ('url', 'id', 'name', 'country', 'is_active', 'type',
                  'storescraper_class')


class CategorySerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Category
        fields = ('url', 'id', 'name',)


class ProductSerializer(serializers.HyperlinkedModelSerializer):
    name = serializers.CharField(read_only=True, source='__str__')
    category = serializers.HyperlinkedRelatedField(
        view_name='category-detail', read_only=True,
        source='category.pk')

    class Meta:
        model = Product
        fields = ('url', 'id', 'name', 'category', 'instance_model_id',
                  'creation_date', 'last_updated', 'picture_url', 'specs')


class NestedProductSerializer(serializers.HyperlinkedModelSerializer):
    name = serializers.CharField(read_only=True, source='__str__')

    class Meta:
        model = Product
        fields = ('url', 'id', 'name')


class StoreScraperSerializer(serializers.Serializer):
    discover_urls_concurrency = serializers.IntegerField(
        source='scraper.preferred_discover_urls_concurrency',
    )
    products_for_url_concurrency = serializers.IntegerField(
        source='scraper.preferred_products_for_url_concurrency',
    )
    async = serializers.BooleanField(
        source='scraper.prefer_async',
    )


class EntityHistoryPartialSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = EntityHistory
        fields = ['timestamp', 'normal_price', 'offer_price',
                  'cell_monthly_payment', 'is_available']


class EntityHistoryFullSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = EntityHistory
        fields = ['timestamp', 'normal_price', 'offer_price',
                  'cell_monthly_payment', 'is_available', 'stock']


class EntityHistorySerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = EntityHistory
        fields = ['timestamp', 'stock', 'normal_price', 'offer_price',
                  'cell_monthly_payment']


class EntityStateSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = EntityState
        fields = ['url', 'id', 'name']


class EntityMinimalSerializer(serializers.HyperlinkedModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name='entity-detail')

    class Meta:
        model = Entity
        fields = (
            'url',
            'id',
            'name'
        )


class EntityWithInlineProductSerializer(
        serializers.HyperlinkedModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name='entity-detail')
    product = NestedProductSerializer()

    class Meta:
        model = Entity
        fields = (
            'url',
            'id',
            'name',
            'product',
            'store'
        )


class EntityConflictSerializer(serializers.Serializer):
    store = serializers.HyperlinkedRelatedField(
        queryset=Store.objects.all(),
        view_name='store-detail'
    )
    category = serializers.HyperlinkedRelatedField(
        queryset=Category.objects.all(),
        view_name='category-detail',
        source='product.category.pk'
    )
    product = NestedProductSerializer()
    cell_plan = NestedProductSerializer()
    entities = EntityMinimalSerializer(many=True)


class EntityFullSerializer(serializers.HyperlinkedModelSerializer):
    active_registry = EntityHistorySerializer(read_only=True)
    product = NestedProductSerializer(read_only=True)
    cell_plan = NestedProductSerializer(read_only=True)
    url = serializers.HyperlinkedIdentityField(view_name='entity-detail')
    external_url = serializers.URLField(source='url')
    picture_urls = serializers.ListField(
        child=serializers.URLField(),
        source='picture_urls_as_list'
    )

    class Meta:
        model = Entity
        fields = (
            'url',
            'id',
            'store',
            'category',
            'state',
            'scraped_category',
            'currency',
            'product',
            'cell_plan',
            'active_registry',
            'name',
            'cell_plan_name',
            'part_number',
            'sku',
            'key',
            'external_url',
            'discovery_url',
            'description',
            'is_visible',
            'last_association_user',
            'last_association',
            'creation_date',
            'last_updated',
            'picture_urls',
            'last_staff_access',
            'last_staff_access_user',
            'last_staff_change',
            'last_staff_change_user',
            'last_pricing_update',
            'last_pricing_update_user',
        )


class StoreUpdateLogSerializer(serializers.HyperlinkedModelSerializer):
    categories = CategorySerializer(many=True)

    class Meta:
        model = StoreUpdateLog
        fields = ('url', 'id', 'store', 'categories', 'status',
                  'creation_date', 'last_updated', 'discovery_url_concurrency',
                  'products_for_url_concurrency', 'use_async', 'registry_file',
                  'available_products_count', 'unavailable_products_count',
                  'discovery_urls_without_products_count')


class EntityEventValueSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField(source='__str__')


class EntityEventUserSerializer(serializers.HyperlinkedModelSerializer):
    full_name = serializers.CharField(source='get_full_name')

    class Meta:
        model = get_user_model()
        fields = ['url', 'id', 'full_name']


class LeadSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Lead
        fields = ['url', 'id', 'user', 'ip']
