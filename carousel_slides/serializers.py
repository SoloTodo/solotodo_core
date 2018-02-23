from rest_framework import serializers

from carousel_slides.models import CarouselSlide


class CarouselSlideSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = CarouselSlide
        fields = ('id', 'name', 'website', 'ordering', 'img_400', 'img_576',
                  'img_768', 'img_992', 'img_1200', 'target_url')
