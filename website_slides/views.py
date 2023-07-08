from django_filters import rest_framework
from rest_framework import viewsets
from rest_framework.filters import OrderingFilter

from website_slides.filters import WebsiteSlideFilterSet
from website_slides.models import WebsiteSlide
from website_slides.serializers import WebsiteSlideSerializer


class WebsiteSlideViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = WebsiteSlide.objects.all()
    serializer_class = WebsiteSlideSerializer
    filter_backends = (rest_framework.DjangoFilterBackend, OrderingFilter)
    filterset_class = WebsiteSlideFilterSet

