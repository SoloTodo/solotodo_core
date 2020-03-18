from rest_framework import serializers

from .models import BrandComparison, BrandComparisonSegment, \
    BrandComparisonSegmentRow, BrandComparisonAlert
from solotodo.models import Category, Brand, Store, Product
from solotodo.serializers import BrandSerializer, NestedProductSerializer, \
    UserSerializer, CategorySerializer

from django.conf import settings


class BrandComparisonSerializer(serializers.HyperlinkedModelSerializer):
    user = UserSerializer()
    brand_1 = BrandSerializer()
    brand_2 = BrandSerializer()
    manual_products = NestedProductSerializer(many=True)

    class Meta:
        model = BrandComparison
        fields = ('id', 'url', 'user', 'name', 'category', 'brand_1',
                  'brand_2', 'price_type', 'stores', 'manual_products')


class BrandComparisonSegmentRowSerializer(
        serializers.HyperlinkedModelSerializer):
    product_1 = NestedProductSerializer()
    product_2 = NestedProductSerializer()

    class Meta:
        model = BrandComparisonSegmentRow
        fields = (
            'id', 'ordering', 'product_1', 'product_2', 'segment',
            'is_product_1_highlighted', 'is_product_2_highlighted')


class BrandComparisonSegmentRowUpdateSerializer(
        serializers.HyperlinkedModelSerializer):
    product_1 = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(), allow_null=True)
    product_2 = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(), allow_null=True)

    class Meta:
        model = BrandComparisonSegmentRow
        fields = ('product_1', 'product_2',
                  'is_product_1_highlighted', 'is_product_2_highlighted')


class BrandComparisonSegmentSerializer(serializers.HyperlinkedModelSerializer):
    rows = BrandComparisonSegmentRowSerializer(many=True)

    class Meta:
        model = BrandComparisonSegment
        fields = ('id', 'url', 'name', 'ordering', 'rows', 'comparison')


class BrandComparisonAlertSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = BrandComparisonAlert
        fields = ('id', 'user', 'brand_comparison', 'stores', 'last_check')


class BrandComparisonAlertCreationSerializer(
        serializers.HyperlinkedModelSerializer):
    brand_comparison = serializers.PrimaryKeyRelatedField(
        queryset=BrandComparison.objects.all())
    stores = serializers.PrimaryKeyRelatedField(
        queryset=Store.objects.all(), many=True)

    @property
    def data(self):
        return BrandComparisonAlertSerializer(
            self.instance, context={'request': self.context['request']}).data

    def validate_stores(self, value):
        user = self.context['request'].user

        for store in value:
            if not user.has_perm('solotodo.view_store', store):
                raise serializers.ValidationError('Permission denied on store')

        return value

    def validate_brand_comparison(self, value):
        user = self.context['request'].user
        group = user.groups.get()

        if user.is_superuser or value.user.groups.get() == group:
            return value

        raise serializers.ValidationError('User not in group')

    def create(self, validated_data):
        user = self.context['request'].user
        brand_comparison = validated_data['brand_comparison']
        stores = validated_data['stores']

        bca = BrandComparisonAlert.objects.create(
            user=user,
            brand_comparison=brand_comparison)

        bca.stores.set(stores)

        return bca

    class Meta:
        model = BrandComparisonAlert
        fields = ('brand_comparison', 'stores')


class FullBrandComparisonSerializer(serializers.HyperlinkedModelSerializer):
    user = UserSerializer()
    brand_1 = BrandSerializer()
    brand_2 = BrandSerializer()
    segments = BrandComparisonSegmentSerializer(many=True)
    category = CategorySerializer()
    manual_products = NestedProductSerializer(many=True)

    class Meta:
        model = BrandComparison
        fields = ('url', 'id', 'user', 'name', 'category', 'brand_1',
                  'brand_2', 'price_type', 'segments', 'stores',
                  'manual_products')


class BrandComparisonUpdateSerializer(serializers.HyperlinkedModelSerializer):
    stores = serializers.PrimaryKeyRelatedField(
        queryset=Store.objects.all(), many=True)

    @property
    def data(self):
        return FullBrandComparisonSerializer(
            self.instance, context={'request': self.context['request']}).data

    class Meta:
        model = BrandComparison
        fields = ('name', 'price_type', 'stores')


class BrandComparisonCreationSerializer(
        serializers.HyperlinkedModelSerializer):
    name = serializers.CharField
    category = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all())
    brand_1 = serializers.PrimaryKeyRelatedField(
        queryset=Brand.objects.all())
    brand_2 = serializers.PrimaryKeyRelatedField(
        queryset=Brand.objects.all())

    @property
    def data(self):
        return BrandComparisonSerializer(
            self.instance, context={'request': self.context['request']}).data

    def validate_category(self, value):
        user = self.context['request'].user

        if not user.has_perm(
                'solotodo.create_category_brand_comparison', value):
            raise serializers.ValidationError('Permission denied on category')

        return value

    def create(self, validated_data):
        user = self.context['request'].user
        name = validated_data['name']
        category = validated_data['category']
        brand_1 = validated_data['brand_1']
        brand_2 = validated_data['brand_2']

        brand_comparison = BrandComparison.objects.create(
            user=user,
            name=name,
            category=category,
            brand_1=brand_1,
            brand_2=brand_2,
        )

        brand_comparison.stores.set(
            settings.BRAND_COMPARISON_DEFAULT_STORE_IDS)

        segment = BrandComparisonSegment.objects.create(
            name='Segmento Inicial',
            ordering=1,
            comparison=brand_comparison)

        BrandComparisonSegmentRow.objects.create(
            ordering=1,
            segment=segment)

        return brand_comparison

    class Meta:
        model = BrandComparison
        fields = ('name', 'category', 'brand_1', 'brand_2')
