from rest_framework import serializers

from .models import BrandComparison, BrandComparisonSegment, \
    BrandComparisonSegmentRow
from solotodo.serializers import BrandSerializer, StoreSerializer,\
    NestedProductSerializer, UserSerializer


class BrandComparisonSerializer(serializers.HyperlinkedModelSerializer):
    user = UserSerializer()
    brand_1 = BrandSerializer()
    brand_2 = BrandSerializer()

    class Meta:
        model = BrandComparison
        fields = ('user', 'name', 'category', 'brand_1', 'brand_2',
                  'price_type', 'stores')


class BrandComparisonSegmentRowSerializer(
        serializers.HyperlinkedModelSerializer):
    product_1 = NestedProductSerializer()
    product_2 = NestedProductSerializer()

    class Meta:
        model = BrandComparisonSegmentRow
        fields = ('ordering', 'product_1', 'product_2', 'segment')


class BrandComparisonSegmentSerializer(serializers.HyperlinkedModelSerializer):
    rows = BrandComparisonSegmentRowSerializer(many=True)

    class Meta:
        model = BrandComparisonSegment
        fields = ('name', 'ordering', 'rows', 'comparison')


class FullBrandComparisonSerializer(serializers.HyperlinkedModelSerializer):
    user = UserSerializer()
    brand_1 = BrandSerializer()
    brand_2 = BrandSerializer()
    segments = BrandComparisonSegmentSerializer(many=True)

    class Meta:
        model = BrandComparison
        fields = ('user', 'name', 'category', 'brand_1', 'brand_2',
                  'price_type', 'segments', 'stores')