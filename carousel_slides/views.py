from django_filters import rest_framework
from rest_framework import viewsets

from carousel_slides.filters import CarouselSlideFilterSet
from carousel_slides.models import CarouselSlide
from carousel_slides.serializers import CarouselSlideSerializer


class CarouselSlideViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CarouselSlide.objects.all()
    serializer_class = CarouselSlideSerializer
    filter_backends = (rest_framework.DjangoFilterBackend,)
    filterset_class = CarouselSlideFilterSet
