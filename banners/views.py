from django.core.exceptions import ValidationError
from django_filters import rest_framework

from rest_framework import viewsets, mixins, status
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.decorators import list_route, detail_route
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from .models import Banner, BannerUpdate, BannerAsset, BannerAssetContent
from .serializers import BannerSerializer, BannerUpdateSerializer,\
    BannerAssetSerializer
from .filters import BannerFilterSet, BannerUpdateFilterSet, \
    BannerAssetFilterSet
from .pagination import BannerPagination, BannerAssetPagination, \
    BannerUpdatePagination
from .forms.add_banner_asset_content_form import AddBannerAssetContentForm


class BannerViewSet(mixins.CreateModelMixin,
                    mixins.RetrieveModelMixin,
                    mixins.ListModelMixin,
                    viewsets.GenericViewSet):
    queryset = Banner.objects.all()
    serializer_class = BannerSerializer
    filter_backends = (rest_framework.DjangoFilterBackend, SearchFilter,
                       OrderingFilter)
    filter_class = BannerFilterSet
    ordering_fields = ('position', 'update__store', 'update__timestamp')
    pagination_class = BannerPagination


class BannerUpdateViewSet(mixins.CreateModelMixin,
                          mixins.RetrieveModelMixin,
                          mixins.ListModelMixin,
                          viewsets.GenericViewSet):

    queryset = BannerUpdate.objects.all()
    serializer_class = BannerUpdateSerializer
    filter_backends = (rest_framework.DjangoFilterBackend, SearchFilter,
                       OrderingFilter)
    filter_class = BannerUpdateFilterSet
    pagination_class = BannerUpdatePagination


class BannerAssetViewSet(mixins.CreateModelMixin,
                         mixins.RetrieveModelMixin,
                         mixins.ListModelMixin,
                         viewsets.GenericViewSet):
    queryset = BannerAsset.objects.all()
    serializer_class = BannerAssetSerializer
    filter_backends = (rest_framework.DjangoFilterBackend, SearchFilter,
                       OrderingFilter)
    filter_class = BannerAssetFilterSet
    ordering_fields = ('id',)
    pagination_class = BannerAssetPagination

    def get_queryset(self):
        user = self.request.user

        if user.has_perm('banners.is_staff_of_banner_assets'):
            return BannerAsset.objects.all()
        else:
            return BannerAsset.objects.none()

    @detail_route(methods=['post'])
    def add_content(self, request, pk, *args, **kwargs):
        user = request.user
        banner_asset = self.get_object()

        if not user.has_perm('banners.is_staff_of_banner_assets'):
            raise PermissionDenied

        form = AddBannerAssetContentForm(request.data)

        if not form.is_valid():
            return Response({
                'errors': form.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            form.add_content(banner_asset)
        except ValidationError as e:
            return Response({
                'errors': {'percentage': [e.message]}
            }, status=status.HTTP_400_BAD_REQUEST)

        serializer = BannerAssetSerializer(banner_asset,
                                           context={'request': request})

        return Response(serializer.data)

    @detail_route(methods=['post'])
    def delete_content(self, request, pk, *args, **kwargs):
        user = request.user
        banner_asset = self.get_object()

        if not user.has_perm('banners.is_staff_of_banner_assets'):
            raise PermissionDenied

        if 'id' not in request.data:
            return Response({
                'error': 'Id not provided'
            }, status=status.HTTP_400_BAD_REQUEST)

        content_id = request.data['id']

        try:
            content = BannerAssetContent.objects.get(id=content_id,
                                                     asset=banner_asset)
        except BannerAssetContent.DoesNotExist:
            return Response({
                'error': 'Invalid id/asset combination'
            }, status=status.HTTP_400_BAD_REQUEST)

        content.delete()

        serializer = BannerAssetSerializer(banner_asset,
                                           context={'request': request})

        return Response(serializer.data)
