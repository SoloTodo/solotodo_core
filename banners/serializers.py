from rest_framework import serializers

from .models import Banner, BannerUpdate, BannerAsset, BannerAssetContent, \
    BannerSection, BannerSubsection, BannerSubsectionType
from solotodo.serializers import CategorySerializer, BrandSerializer


class BannerUpdateSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = BannerUpdate
        fields = ('id', 'url', 'store', 'status', 'status_message',
                  'is_active', 'timestamp')


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
        fields = ('id', 'url', 'name')


class BannerSubsectionTypeSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = BannerSubsectionType
        fields = ('id', 'url', 'name')


class BannerSubsectionSerializer(serializers.HyperlinkedModelSerializer):
    section = BannerSectionSerializer()
    type = BannerSubsectionTypeSerializer()

    class Meta:
        model = BannerSubsection
        fields = ('id', 'name', 'section', 'type')


class BannerSerializer(serializers.HyperlinkedModelSerializer):
    update = BannerUpdateSerializer()
    asset = BannerAssetSerializer()
    subsection = BannerSubsectionSerializer()
    url = serializers.HyperlinkedIdentityField(view_name='banner-detail')
    external_url = serializers.URLField(source='url')

    class Meta:
        model = Banner
        fields = ('id', 'update', 'external_url', 'url',
                  'destination_url_list', 'subsection', 'asset', 'position')
