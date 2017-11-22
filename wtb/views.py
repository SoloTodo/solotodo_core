from django_filters import rest_framework
from rest_framework import viewsets
from rest_framework.filters import SearchFilter, OrderingFilter

from solotodo.drf_extensions import PermissionReadOnlyModelViewSet
from wtb.filters import create_wtb_brand_filter, WtbEntityFilterSet, \
    WtbBrandUpdateLogFilterSet
from wtb.models import WtbBrand, WtbEntity, WtbBrandUpdateLog
from wtb.pagination import WtbEntityPagination, WtbStoreUpdateLogPagination
from wtb.serializers import WtbBrandSerializer, WtbEntitySerializer, \
    WtbBrandUpdateLogSerializer


class WtbBrandViewSet(PermissionReadOnlyModelViewSet):
    queryset = WtbBrand.objects.all()
    serializer_class = WtbBrandSerializer

    def get_queryset(self):
        return create_wtb_brand_filter()(self.request)


class WtbEntityViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = WtbEntity.objects.all()
    serializer_class = WtbEntitySerializer
    pagination_class = WtbEntityPagination
    filter_backends = (rest_framework.DjangoFilterBackend, SearchFilter,
                       OrderingFilter)
    filter_class = WtbEntityFilterSet
    ordering_fields = ('last_updated',)


class WtbBrandUpdateLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = WtbBrandUpdateLog.objects.all()
    serializer_class = WtbBrandUpdateLogSerializer
    pagination_class = WtbStoreUpdateLogPagination
    filter_backends = (rest_framework.DjangoFilterBackend, OrderingFilter)
    filter_class = WtbBrandUpdateLogFilterSet
    ordering_fields = ('last_updated', )
