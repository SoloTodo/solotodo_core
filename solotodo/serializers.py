from django.contrib.auth import get_user_model
from guardian.utils import get_anonymous_user
from rest_framework import serializers
from rest_framework.reverse import reverse

from hardware.models import Budget
from metamodel.models import InstanceModel
from solotodo.models import Language, Store, Currency, Country, StoreType, \
    Category, StoreUpdateLog, Entity, EntityHistory, Product, NumberFormat, \
    Lead, Website, CategorySpecsFilter, CategorySpecsOrder, Visit, Rating, \
    ProductPicture, Brand, StoreSection, EntitySectionPosition, ProductVideo, \
    Bundle, Coupon
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


class NestedProductSerializer(serializers.HyperlinkedModelSerializer):
    name = serializers.CharField(read_only=True, source='__str__')

    class Meta:
        model = Product
        fields = ('url', 'id', 'name')


class MyUserSerializer(serializers.HyperlinkedModelSerializer):
    class InlineBudgetSerializer(serializers.HyperlinkedModelSerializer):
        class Meta:
            model = Budget
            fields = ['id', 'name', 'creation_date']

    detail_url = serializers.HyperlinkedRelatedField(
        view_name='solotodouser-detail', read_only=True, source='pk')
    budgets = InlineBudgetSerializer(many=True)

    preferred_store = serializers.SerializerMethodField()

    def get_preferred_store(self, obj):
        group = obj.groups.all()[0]
        request = self.context['request']
        try:
            return reverse(
                'store-detail',
                args=[group.preferred_store.id],
                request=request)
        except Store.DoesNotExist:
            return None

    class Meta:
        model = get_user_model()
        fields = ('url', 'id', 'name', 'detail_url', 'email', 'first_name',
                  'last_name', 'preferred_language', 'preferred_country',
                  'preferred_currency', 'preferred_number_format',
                  'preferred_store', 'preferred_stores_last_updated',
                  'preferred_stores', 'preferred_exclude_refurbished',
                  'date_joined', 'is_staff', 'permissions', 'budgets',
                  'is_superuser')
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
                  'storescraper_class', 'logo', 'preferred_payment_method')


class BundleSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Bundle
        fields = ('url', 'id', 'name')


class BundleModelSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        serializer = BundleSerializer(instance, context={'request': self.context['request']})
        return serializer.data

    class Meta:
        model = Bundle
        fields = ['name']


class CouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = ['code', 'amount', 'amount_type', 'amount_type_text']


class CategorySerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Category
        fields = ('url', 'id', 'name', 'slug', 'budget_ordering',
                  'short_description_template', 'browse_result_template',
                  'detail_template')


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
                  'creation_date', 'last_updated', 'picture_url', 'brand',
                  'part_number', 'specs', 'keywords')


class StaffProductSerializer(ProductSerializer):
    creator = UserSerializer()

    class Meta:
        model = Product
        fields = ('url', 'id', 'name', 'category', 'slug', 'instance_model_id',
                  'creation_date', 'last_updated', 'picture_url', 'brand',
                  'part_number', 'specs', 'creator', 'keywords')


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
    prefer_async = serializers.BooleanField(
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
    bundle = BundleSerializer()

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
            'bundle',
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
    bundle = BundleSerializer()
    entities = EntityMinimalSerializer(many=True)


class EntitySerializer(serializers.HyperlinkedModelSerializer):
    active_registry = EntityHistorySerializer(read_only=True)
    product = NestedProductSerializer(read_only=True)
    cell_plan = NestedProductSerializer(read_only=True)
    bundle = BundleSerializer(read_only=True)
    best_coupon = CouponSerializer(read_only=True)
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
            'bundle',
            'best_coupon',
            'currency',
            'description',
            'picture_urls',
            'key',
            'seller',
            'scraped_condition',
            'creation_date',
            'last_updated',
            'last_pricing_update',
        )


class EntityWithoutDescriptionSerializer(EntitySerializer):
    bundle = BundleSerializer()

    class Meta:
        model = Entity
        fields = (
            'url',
            'id',
            'name',
            'cell_plan_name',
            'store',
            'bundle',
            'best_coupon',
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
            'seller',
            'key',
            'creation_date',
            'last_updated',
            'last_pricing_update',
        )


class EntityHistoryWithNestedEntitySerializer(
        serializers.HyperlinkedModelSerializer):
    entity = EntityWithoutDescriptionSerializer()

    class Meta:
        model = EntityHistory
        fields = ['url', 'id', 'entity', 'timestamp', 'is_available',
                  'normal_price', 'offer_price', 'cell_monthly_payment']


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
            'brand'
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


class ProductAvailableEntitiesMinimalSerializer(serializers.Serializer):
    class CustomEntitySerializer(serializers.HyperlinkedModelSerializer):
        class EntityHistoryCustomSerializer(
                serializers.HyperlinkedModelSerializer):
            class Meta:
                model = EntityHistory
                fields = ['id', 'normal_price', 'offer_price']

        active_registry = EntityHistoryCustomSerializer()
        best_coupon = CouponSerializer()
        external_url = serializers.URLField(source='url')

        class Meta:
            model = Entity
            fields = (
                'id',
                'store',
                'external_url',
                'active_registry',
                'best_coupon'
            )

    product = ProductSerializer()
    entities = CustomEntitySerializer(many=True)


class RatingSerializer(serializers.ModelSerializer):
    product = NestedProductSerializer()
    store = serializers.HyperlinkedRelatedField(
        view_name='store-detail', read_only=True,
        source='store.pk')

    class Meta:
        model = Rating
        fields = ('id', 'url', 'product', 'product_rating', 'product_comments',
                  'store', 'store_rating', 'store_comments', 'creation_date',
                  'approval_date', 'status', 'last_updated')


class RatingFullSerializer(RatingSerializer):
    user = UserSerializer()

    class Meta:
        model = Rating
        fields = ('id', 'url', 'product', 'product_rating', 'product_comments',
                  'store', 'store_rating', 'store_comments', 'creation_date',
                  'user', 'ip', 'purchase_proof', 'approval_date',
                  'email_or_phone', 'status', 'last_updated')


class RatingCreateSerializer(serializers.ModelSerializer):
    store_rating = serializers.IntegerField(min_value=1, max_value=5)
    product_rating = serializers.IntegerField(min_value=1, max_value=5,
                                              allow_null=True, required=False)
    email_or_phone = serializers.CharField(max_length=255,
                                           allow_null=False, required=True)
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
                  'store', 'store_rating', 'store_comments', 'purchase_proof',
                  'email_or_phone')


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


class BrandSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Brand
        fields = ('id', 'url', 'name')


class StoreSectionSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = StoreSection
        fields = ('id', 'url', 'name', 'store')


class EntitySectionPositionSerializer(serializers.HyperlinkedModelSerializer):
    entity_history = EntityHistorySerializer()
    section = StoreSectionSerializer()

    class Meta:
        model = EntitySectionPosition
        fields = ('id', 'url', 'value', 'entity_history', 'section')


class ProductVideoSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = ProductVideo
        fields = ('id', 'url', 'youtube_id', 'name', 'conditions')
