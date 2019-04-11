from rest_framework import serializers

from .models import BrandComparison, BrandComparisonSegment, \
    BrandComparisonSegmentRow
from solotodo.models import Category, Brand, Store, Product
from solotodo.serializers import BrandSerializer, NestedProductSerializer, \
    UserSerializer, CategorySerializer

from django.conf import settings


class BrandComparisonSerializer(serializers.HyperlinkedModelSerializer):
    user = UserSerializer()
    brand_1 = BrandSerializer()
    brand_2 = BrandSerializer()

    class Meta:
        model = BrandComparison
        fields = ('id', 'url', 'user', 'name', 'category', 'brand_1', 'brand_2',
                  'price_type', 'stores')


class BrandComparisonSegmentRowSerializer(
        serializers.HyperlinkedModelSerializer):
    product_1 = NestedProductSerializer()
    product_2 = NestedProductSerializer()

    class Meta:
        model = BrandComparisonSegmentRow
        fields = ('id', 'ordering', 'product_1', 'product_2', 'segment')


class BrandComparisonSegmentRowUpdateSerializer(
        serializers.HyperlinkedModelSerializer):
    product_1 = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(), allow_null=True)
    product_2 = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(), allow_null=True)

    class Meta:
        model = BrandComparisonSegmentRow
        fields = ('product_1', 'product_2')


class BrandComparisonSegmentSerializer(serializers.HyperlinkedModelSerializer):
    rows = BrandComparisonSegmentRowSerializer(many=True)

    class Meta:
        model = BrandComparisonSegment
        fields = ('id', 'url', 'name', 'ordering', 'rows', 'comparison')


class FullBrandComparisonSerializer(serializers.HyperlinkedModelSerializer):
    user = UserSerializer()
    brand_1 = BrandSerializer()
    brand_2 = BrandSerializer()
    segments = BrandComparisonSegmentSerializer(many=True)
    category = CategorySerializer()

    class Meta:
        model = BrandComparison
        fields = ('url', 'id', 'user', 'name', 'category', 'brand_1', 'brand_2',
                  'price_type', 'segments', 'stores')


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
