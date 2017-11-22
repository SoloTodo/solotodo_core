from rest_framework import serializers

from solotodo.serializers import NestedProductSerializer
from wtb.models import WtbBrand, WtbEntity, WtbBrandUpdateLog


class WtbBrandSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = WtbBrand
        fields = ('url', 'id', 'name', 'prefered_brand', 'storescraper_class',
                  'stores')


class WtbEntitySerializer(serializers.HyperlinkedModelSerializer):
    external_url = serializers.URLField(source='url')
    product = NestedProductSerializer(read_only=True)

    class Meta:
        model = WtbEntity
        fields = ('url', 'id', 'name', 'brand', 'category', 'external_url',
                  'product', 'key', 'picture_url', 'creation_date',
                  'last_updated', 'is_visible', 'is_active')


class WtbBrandUpdateLogSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = WtbBrandUpdateLog
        fields = ('url', 'id', 'brand', 'status',
                  'creation_date', 'last_updated', 'registry_file')
