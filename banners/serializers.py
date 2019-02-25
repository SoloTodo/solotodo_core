from rest_framework import serializers

from .models import Banner, BannerUpdate, BannerAsset, BannerAssetContent, \
    BannerSection
from solotodo.serializers import CategorySerializer, BrandSerializer


class BannerUpdateSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = BannerUpdate
        fields = ('id', 'url', 'store', 'is_active', 'timestamp')


class BannerAssetContentSerializer(serializers.HyperlinkedModelSerializer):
    category = CategorySerializer()
    brand = BrandSerializer()

    class Meta:
        model = BannerAssetContent
        fields = ('id', 'brand', 'category', 'percentage')


class BannerAssetSerializer(serializers.HyperlinkedModelSerializer):
    contents = BannerAssetContentSerializer(many=True)

    class Meta:
        model = BannerAsset
        fields = ('url', 'id', 'key', 'picture_url', 'contents', 'is_active',
                  'is_complete', 'total_percentage', 'creation_date')


class BannerSectionSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = BannerSection
        fields = ('url', 'id', 'name', 'category',)


class BannerSerializer(serializers.HyperlinkedModelSerializer):
    update = BannerUpdateSerializer()
    asset = BannerAssetSerializer()
    section = BannerSectionSerializer()

    class Meta:
        model = Banner
        fields = ('id', 'update', 'section', 'asset', 'position')
