from django.contrib.auth import get_user_model
from guardian.utils import get_anonymous_user
from rest_framework import serializers
from sorl.thumbnail import get_thumbnail

from hardware.models import Budget
from metamodel.models import InstanceModel
from solotodo.models import Language, Store, Currency, Country, StoreType, \
    Category, StoreUpdateLog, Entity, EntityHistory, Product, NumberFormat, \
    Lead, Website, CategorySpecsFilter, CategorySpecsOrder, Visit, Rating, \
    SoloTodoUser, ProductPicture
from solotodo.serializer_utils import StorePrimaryKeyRelatedField, \
    ProductPrimaryKeyRelatedField
from solotodo.utils import get_client_ip


class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ('url', 'id', 'name', 'email', 'first_name', 'last_name',
                  'date_joined', 'is_staff')


class WebsiteSerializer(serializers.HyperlinkedModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name='website-detail')
    external_url = serializers.URLField(source='url')

    class Meta:
        model = Website
        fields = ('url', 'id', 'name', 'external_url')


class InlineBudgetSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Budget
        fields = ['id', 'name', 'creation_date']


class MyUserSerializer(serializers.HyperlinkedModelSerializer):
    detail_url = serializers.HyperlinkedRelatedField(
        view_name='solotodouser-detail', read_only=True, source='pk')
    budgets = InlineBudgetSerializer(many=True)

    class Meta:
        model = get_user_model()
        fields = ('url', 'id', 'name', 'detail_url', 'email', 'first_name',
                  'last_name', 'preferred_language', 'preferred_country',
                  'preferred_currency', 'preferred_number_format',
                  'preferred_store', 'preferred_stores_last_updated',
                  'preferred_stores', 'date_joined', 'is_staff',
                  'permissions', 'budgets', 'is_superuser')
        read_only_fields = ('email', 'first_name', 'last_name',
                            'permissions', 'is_staff', 'is_superuser',
                            'budgets', 'date_joined')


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
        fields = ('url', 'id', 'name', 'thousands_separator',
                  'decimal_separator')


class CurrencySerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Currency
        fields = ('url', 'id', 'name', 'iso_code', 'decimal_places', 'prefix',
                  'exchange_rate', 'exchange_rate_last_updated')


class CountrySerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Country
        fields = ('url', 'id', 'name', 'iso_code', 'currency', 'number_format',
                  'flag')


class StoreSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Store
        fields = ('url', 'id', 'name', 'country', 'last_activation', 'type',
                  'storescraper_class', 'logo')


class CategorySerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Category
        fields = ('url', 'id', 'name', 'slug', 'budget_ordering')


class CategorySpecsFilterChoiceSerializer(
        serializers.HyperlinkedModelSerializer):
    label = serializers.CharField(source='unicode_representation')

    class Meta:
        model = InstanceModel
        fields = ['id', 'label']


class CategorySpecsFilterSerializer(serializers.HyperlinkedModelSerializer):
    choices = CategorySpecsFilterChoiceSerializer(many=True)

    class Meta:
        model = CategorySpecsFilter
        fields = ('name', 'type', 'choices')


class CategorySpecsOrderSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = CategorySpecsOrder
        fields = ('name', )


class ProductSerializer(serializers.HyperlinkedModelSerializer):
    name = serializers.CharField(read_only=True, source='__str__')
    slug = serializers.CharField(read_only=True)
    category = serializers.HyperlinkedRelatedField(
        view_name='category-detail', read_only=True,
        source='category.pk')

    class Meta:
        model = Product
        fields = ('url', 'id', 'name', 'category', 'slug', 'instance_model_id',
                  'creation_date', 'last_updated', 'picture_url',
                  'specs')


class NestedProductSerializer(serializers.HyperlinkedModelSerializer):
    name = serializers.CharField(read_only=True, source='__str__')

    class Meta:
        model = Product
        fields = ('url', 'id', 'name')


class NestedProductSerializerWithCategory(NestedProductSerializer):
    category = serializers.HyperlinkedRelatedField(
        view_name='category-detail', read_only=True,
        source='category.pk')

    class Meta:
        model = Product
        fields = ('url', 'id', 'name', 'category')


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


class EntityHistoryWithStockSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = EntityHistory
        fields = ['url', 'id', 'timestamp', 'normal_price', 'offer_price',
                  'cell_monthly_payment', 'is_available', 'stock']


class EntityHistorySerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = EntityHistory
        fields = ['url', 'id', 'entity', 'timestamp', 'is_available',
                  'normal_price', 'offer_price', 'cell_monthly_payment']


class EntityMinimalSerializer(serializers.HyperlinkedModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name='entity-detail')

    class Meta:
        model = Entity
        fields = ['url', 'id', 'name', 'category', 'store']


class EntityWithInlineProductSerializer(
        serializers.HyperlinkedModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name='entity-detail')
    external_url = serializers.URLField(source='url')
    product = NestedProductSerializer()

    class Meta:
        model = Entity
        fields = (
            'url',
            'id',
            'name',
            'category',
            'currency',
            'external_url',
            'product',
            'store',
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


class EntitySerializer(serializers.HyperlinkedModelSerializer):
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
            'name',
            'cell_plan_name',
            'store',
            'category',
            'sku',
            'external_url',
            'condition',
            'part_number',
            'ean',
            'is_visible',
            'active_registry',
            'product',
            'cell_plan',
            'currency',
            'description',
            'picture_urls',
            'key',
            'creation_date',
            'last_updated',
            'last_pricing_update',
        )


class EntityWithoutDescriptionSerializer(EntitySerializer):
    class Meta:
        model = Entity
        fields = (
            'url',
            'id',
            'name',
            'cell_plan_name',
            'store',
            'category',
            'sku',
            'external_url',
            'condition',
            'part_number',
            'ean',
            'is_visible',
            'active_registry',
            'product',
            'cell_plan',
            'currency',
            'picture_urls',
            'key',
            'creation_date',
            'last_updated',
            'last_pricing_update',
        )


class EntityStaffInfoSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Entity
        fields = (
            'discovery_url',
            'scraped_category',
            'last_association_user',
            'last_association',
            'last_staff_access',
            'last_staff_access_user',
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
    normal_price = serializers.DecimalField(
        source='entity_history.normal_price',
        max_digits=20,
        decimal_places=2
    )
    offer_price = serializers.DecimalField(
        source='entity_history.offer_price',
        max_digits=20,
        decimal_places=2
    )
    entity = EntityWithInlineProductSerializer(
        source='entity_history.entity'
    )

    class Meta:
        model = Lead
        fields = ['url', 'id', 'timestamp', 'normal_price',
                  'offer_price', 'website', 'entity']


class LeadWithUserDataSerializer(LeadSerializer):
    user = UserSerializer()

    class Meta:
        model = Lead
        fields = ['url', 'id', 'user', 'ip', 'timestamp', 'normal_price',
                  'offer_price', 'website', 'entity']


class VisitSerializer(serializers.HyperlinkedModelSerializer):
    product = NestedProductSerializerWithCategory()

    class Meta:
        model = Visit
        fields = ['url', 'id', 'product', 'website', 'timestamp']


class VisitWithUserDataSerializer(VisitSerializer):
    user = UserSerializer()

    class Meta:
        model = Visit
        fields = ['url', 'id', 'product', 'website', 'timestamp', 'user', 'ip']


class CategoryBrowsePricesSerializer(serializers.Serializer):
    currency = serializers.HyperlinkedRelatedField(
        view_name='currency-detail', read_only=True, source='currency.id')
    min_normal_price = serializers.DecimalField(
        max_digits=None, decimal_places=2)
    min_offer_price = serializers.DecimalField(
        max_digits=None, decimal_places=2)
    min_normal_price_usd = serializers.DecimalField(
        max_digits=None, decimal_places=2)
    min_offer_price_usd = serializers.DecimalField(
        max_digits=None, decimal_places=2)

    class Meta:
        fields = ['currency', 'min_normal_price', 'min_offer_price',
                  'min_normal_price_usd', 'min_offer_price_usd']


class CategoryBrowseProductEntrySerializer(serializers.Serializer):
    product = ProductSerializer()
    ordering_value = serializers.DecimalField(max_digits=20, decimal_places=2)
    prices = CategoryBrowsePricesSerializer(many=True)

    class Meta:
        fields = ['product', 'ordering_value', 'prices']


class CategoryBrowseResultSerializer(serializers.Serializer):
    bucket = serializers.CharField()
    product_entries = CategoryBrowseProductEntrySerializer(many=True)

    class Meta:
        fields = ['bucket', 'product_entries']


class CategoryFullBrowseResultEntityHistorySerializer(
        serializers.HyperlinkedModelSerializer):
    class Meta:
        model = EntityHistory
        fields = (
            'normal_price',
            'offer_price'
        )


class CategoryFullBrowseResultEntitySerializer(
        serializers.HyperlinkedModelSerializer):
    active_registry = CategoryFullBrowseResultEntityHistorySerializer(
        read_only=True)
    external_url = serializers.URLField(source='url')
    normal_price_usd = serializers.DecimalField(
        max_digits=15, decimal_places=2)
    offer_price_usd = serializers.DecimalField(
        max_digits=15, decimal_places=2)

    class Meta:
        model = Entity
        fields = (
            'id',
            'sku',
            'store',
            'external_url',
            'active_registry',
            'currency',
            'normal_price_usd',
            'offer_price_usd',
        )


class CategoryFullBrowseResultProductSerializer(
        serializers.HyperlinkedModelSerializer):
    name = serializers.CharField(read_only=True, source='__str__')

    class Meta:
        model = Product
        fields = (
            'id',
            'name',
            'specs',
        )


class CategoryFullBrowseResultSerializer(serializers.Serializer):
    product = CategoryFullBrowseResultProductSerializer()
    cell_plan = NestedProductSerializer()
    entities = CategoryFullBrowseResultEntitySerializer(many=True)

    class Meta:
        fields = ['product', 'cell_plan', 'entities']


class ProductPricingHistorySerializer(serializers.Serializer):
    entity = EntitySerializer()
    pricing_history = EntityHistorySerializer(many=True)


class ProductAvailableEntitiesSerializer(serializers.Serializer):
    product = ProductSerializer()
    entities = EntityWithoutDescriptionSerializer(many=True)


class RatingSerializer(serializers.ModelSerializer):
    product = NestedProductSerializer()
    store = serializers.HyperlinkedRelatedField(
        view_name='store-detail', read_only=True,
        source='store.pk')

    class Meta:
        model = Rating
        fields = ('id', 'url', 'product', 'product_rating', 'product_comments',
                  'store', 'store_rating', 'store_comments', 'creation_date',
                  'approval_date')


class RatingFullSerializer(RatingSerializer):
    user = UserSerializer()

    class Meta:
        model = Rating
        fields = ('id', 'url', 'product', 'product_rating', 'product_comments',
                  'store', 'store_rating', 'store_comments', 'creation_date',
                  'user', 'ip', 'purchase_proof', 'approval_date')


class RatingCreateSerializer(serializers.ModelSerializer):
    store_rating = serializers.IntegerField(min_value=1, max_value=5)
    product_rating = serializers.IntegerField(min_value=1, max_value=5)
    store = StorePrimaryKeyRelatedField()
    product = ProductPrimaryKeyRelatedField()

    def create(self, validated_data):
        if self.context['request'].user.is_authenticated:
            user = self.context['request'].user
        else:
            user = get_anonymous_user()

        validated_data['user'] = user
        validated_data['ip'] = \
            get_client_ip(self.context['request']) or '127.0.0.1'
        return super(RatingCreateSerializer, self).create(validated_data)

    class Meta:
        model = Rating
        fields = ('product', 'product_rating', 'product_comments',
                  'store', 'store_rating', 'store_comments', 'purchase_proof')


class StoreRatingSerializer(serializers.Serializer):
    store = serializers.HyperlinkedRelatedField(
        view_name='store-detail', read_only=True,
        source='store.pk')
    rating = serializers.FloatField()


class ProductPictureSerializer(serializers.HyperlinkedModelSerializer):
    product = NestedProductSerializer()

    class Meta:
        model = ProductPicture
        fields = ('id', 'url', 'product', 'ordering', 'file')
