from rest_framework import serializers

from .models import Banner, BannerUpdate, BannerAsset, BannerAssetContent
from solotodo.serializers import CategorySerializer, BrandSerializer


class BannerUpdateSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = BannerUpdate
        fields = ('store', 'is_active', 'timestamp')


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
                  'is_complete', 'creation_date')


class BannerSerializer(serializers.HyperlinkedModelSerializer):
    update = BannerUpdateSerializer()
    asset = BannerAssetSerializer()

    class Meta:
        model = Banner
        fields = ('id', 'update', 'category', 'asset', 'position')
