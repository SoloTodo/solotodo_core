from rest_framework import serializers

from .models import MicrositeBrand, MicrositeEntry
from solotodo.serializers import NestedProductSerializerWithCategory


class MicrositeEntrySerializer(serializers.HyperlinkedModelSerializer):
    product = NestedProductSerializerWithCategory()

    class Meta:
        model = MicrositeEntry
        fields = ('brand', 'product', 'ordering', 'home_ordering', 'sku',
                  'brand_url', 'title', 'description', 'reference_price',
                  'custom_attr_1_str')


class MicrositeBrandSerializer(serializers.HyperlinkedModelSerializer):
    entries = MicrositeEntrySerializer(many=True)

    class Meta:
        model = MicrositeBrand
        fields = ('name', 'fields', 'entries')
