from rest_framework import serializers

from .models import MicrositeBrand, MicrositeEntry
from solotodo.models import Entity, EntityHistory
from solotodo.serializers import \
    NestedProductSerializerWithCategory, ProductSerializer, BrandSerializer


class MicrositeEntrySerializer(serializers.HyperlinkedModelSerializer):
    product = NestedProductSerializerWithCategory()

    class Meta:
        model = MicrositeEntry
        fields = ('url', 'id', 'brand', 'product', 'ordering', 'home_ordering',
                  'sku', 'brand_url', 'title', 'subtitle', 'description',
                  'reference_price', 'custom_attr_1_str', 'custom_attr_2_str',
                  'custom_attr_3_str', 'custom_attr_4_str',
                  'custom_attr_5_str')


class MicrositeEntryWithoutProductSerializer(
        serializers.HyperlinkedModelSerializer):

    class Meta:
        model = MicrositeEntry
        fields = (
            'url', 'id', 'brand', 'ordering', 'home_ordering', 'sku',
            'brand_url', 'title', 'subtitle', 'description', 'reference_price',
            'custom_attr_1_str', 'custom_attr_2_str', 'custom_attr_3_str',
            'custom_attr_4_str', 'custom_attr_5_str')


class MicrositeEntrySiteSerializer(serializers.Serializer):
    class CustomEntitySerializer(serializers.HyperlinkedModelSerializer):
        class EntityHistoryCustomSerializer(
                serializers.HyperlinkedModelSerializer):
            class Meta:
                model = EntityHistory
                fields = ['id', 'normal_price', 'offer_price']

        active_registry = EntityHistoryCustomSerializer()
        external_url = serializers.URLField(source='url')

        class Meta:
            model = Entity
            fields = (
                'id',
                'store',
                'external_url',
                'active_registry')

    metadata = MicrositeEntryWithoutProductSerializer()
    product = ProductSerializer()
    entities = CustomEntitySerializer(many=True)


class MicrositeBrandSerializer(serializers.HyperlinkedModelSerializer):
    brand = BrandSerializer()
    entries = MicrositeEntrySerializer(many=True)

    class Meta:
        model = MicrositeBrand
        fields = ('url', 'id', 'name', 'brand', 'fields', 'entries')
