from rest_framework import serializers

from .models import Banner, BannerUpdate, BannerAsset, BannerAssetContent
from solotodo.serializers import CategorySerializer


class BannerUpdateSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = BannerUpdate
        fields = ('store', 'timestamp')


class BannerAssetSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = BannerAsset
        fields = ('key', 'picture_url', 'creation_date')


class BannerAssetContentSerializer(serializers.HyperlinkedModelSerializer):
    asset = BannerAssetSerializer()
    category = CategorySerializer()

    class Meta:
        model = BannerAssetContent
        fields = ('asset', 'brand', 'category', 'percentage')


class BannerSerializer(serializers.HyperlinkedModelSerializer):
    update = BannerUpdateSerializer()
    asset = BannerAssetSerializer()

    class Meta:
        model = Banner
        fields = ('update', 'asset', 'position')
