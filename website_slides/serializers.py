from rest_framework import serializers

from website_slides.models import WebsiteSlideAsset, WebsiteSlide


class WebsiteSlideAssetSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = WebsiteSlideAsset
        fields = ('id', 'picture', 'theme_color')


class WebsiteSlideSerializer(serializers.HyperlinkedModelSerializer):
    asset = WebsiteSlideAssetSerializer()

    class Meta:
        model = WebsiteSlide
        fields = ('url', 'id', 'asset', 'label', 'destination_url', 'categories',
                  'category_priority', 'home_priority')
