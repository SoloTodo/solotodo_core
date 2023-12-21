from rest_framework import serializers

from solotodo.serializers import NestedProductSerializer, CategorySerializer
from wtb.models import WtbBrand, WtbEntity, WtbBrandUpdateLog


class WtbBrandSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = WtbBrand
        fields = ('url', 'id', 'name', 'prefered_brand', 'storescraper_class',
                  'stores', 'website')


class WtbEntityMinimalSerializer(serializers.HyperlinkedModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name='wtbentity-detail')
    external_url = serializers.URLField(source='url')

    class Meta:
        model = WtbEntity
        fields = ('url', 'id', 'name', 'model_name', 'brand',
                  'category', 'external_url', 'key', 'picture_url',
                  'creation_date', 'last_updated', 'is_visible', 'is_active')


class WtbEntitySerializer(serializers.HyperlinkedModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name='wtbentity-detail')
    external_url = serializers.URLField(source='url')
    product = NestedProductSerializer(read_only=True)
    brand = WtbBrandSerializer(read_only=True)
    full_category = CategorySerializer(read_only=True, source='category')

    class Meta:
        model = WtbEntity
        fields = ('url', 'id', 'name', 'model_name', 'brand', 'category',
                  'full_category', 'external_url', 'product', 'key',
                  'picture_url', 'section', 'creation_date', 'last_updated',
                  'is_visible', 'is_active', 'price', 'description')


class WtbEntityStaffInfoSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = WtbEntity
        fields = (
            'last_association_user',
            'last_association',
        )


class WtbBrandUpdateLogSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = WtbBrandUpdateLog
        fields = ('url', 'id', 'brand', 'status',
                  'creation_date', 'last_updated', 'registry_file')
