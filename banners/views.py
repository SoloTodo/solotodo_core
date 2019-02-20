from django_filters import rest_framework

from rest_framework import viewsets, mixins
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import Banner, BannerUpdate, BannerAsset
from .serializers import BannerSerializer, BannerUpdateSerializer,\
    BannerAssetSerializer
from .filters import BannerFilterSet, BannerUpdateFilterSet, \
    BannerAssetFilterSet


class BannerViewSet(mixins.CreateModelMixin,
                    mixins.RetrieveModelMixin,
                    mixins.ListModelMixin,
                    viewsets.GenericViewSet):
    queryset = Banner.objects.all()
    serializer_class = BannerSerializer
    filter_backends = (rest_framework.DjangoFilterBackend, SearchFilter,
                       OrderingFilter)
    filter_class = BannerFilterSet
    ordering_fields = ('position',)


class BannerUpdateViewSet(mixins.CreateModelMixin,
                          mixins.RetrieveModelMixin,
                          mixins.ListModelMixin,
                          viewsets.GenericViewSet):

    queryset = BannerUpdate.objects.all()
    serializer_class = BannerUpdateSerializer
    filter_backends = (rest_framework.DjangoFilterBackend, SearchFilter)
    filter_class = BannerUpdateFilterSet


class BannerAssetViewSet(mixins.CreateModelMixin,
                         mixins.RetrieveModelMixin,
                         mixins.ListModelMixin,
                         viewsets.GenericViewSet):
    queryset = BannerAsset.objects.all()
    serializer_class = BannerAssetSerializer
    filter_backends = (rest_framework.DjangoFilterBackend, SearchFilter)
    filter_class = BannerAssetFilterSet

    def get_queryset(self):
        user = self.request.user

        if user.has_perm('banners.is_staff_of_banner_assets'):
            return BannerAsset.objects.all()
        else:
            return BannerAsset.objects.none()
