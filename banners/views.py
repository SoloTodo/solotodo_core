from django.core.exceptions import ValidationError
from django_filters import rest_framework

from rest_framework import viewsets, mixins, status
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.reverse import reverse

from solotodo.filter_querysets import create_store_filter
from .models import Banner, BannerUpdate, BannerAsset, BannerAssetContent, \
    BannerSection, BannerSubsectionType
from .serializers import BannerSerializer, BannerUpdateSerializer, \
    BannerAssetSerializer, BannerSectionSerializer, \
    BannerSubsectionTypeSerializer
from .filters import BannerFilterSet, BannerUpdateFilterSet, \
    BannerAssetFilterSet
from .pagination import BannerPagination, BannerAssetPagination, \
    BannerUpdatePagination
from .forms.add_banner_asset_content_form import AddBannerAssetContentForm
from .forms.banner_active_participation_form import \
    BannerActiveParticipationForm
from .forms.banner_historic_participation_form import \
    BannerHistoricParticipationForm

from solotodo_core.s3utils import PrivateS3Boto3Storage


class BannerViewSet(mixins.RetrieveModelMixin,
                    mixins.ListModelMixin,
                    viewsets.GenericViewSet):
    queryset = Banner.objects.all()
    serializer_class = BannerSerializer
    filter_backends = (rest_framework.DjangoFilterBackend, SearchFilter,
                       OrderingFilter)
    filter_class = BannerFilterSet
    ordering_fields = ('position', 'update__store', 'update__timestamp',
                       'subsection', 'id')
    pagination_class = BannerPagination

    @action(methods=['get'], detail=False)
    def active_participation(self, request):
        user = request.user
        form = BannerActiveParticipationForm(user, request.GET)

        if not form.is_valid():
            return Response({
                'errors': form.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        if form.cleaned_data['response_format'] == 'xls':
            report_path = form.get_banner_participation_as_xls()['path']
            storage = PrivateS3Boto3Storage()
            report_url = storage.url(report_path)
            return Response({
                'url': report_url
            })
        else:
            result = form.get_banner_participation_as_json()
            return Response(result)

    @action(methods=['get'], detail=False)
    def historic_active_participation(self, request):
        user = request.user
        form = BannerHistoricParticipationForm(user, request.GET)

        if not form.is_valid():
            return Response({
                'errors': form.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        report_path = form.generate_report()['path']
        storage = PrivateS3Boto3Storage()
        report_url = storage.url(report_path)
        return Response({
            'url': report_url
        })


class BannerSectionViewSet(mixins.RetrieveModelMixin,
                           mixins.ListModelMixin,
                           viewsets.GenericViewSet):
    queryset = BannerSection.objects.all()
    serializer_class = BannerSectionSerializer


class BannerSubsectionTypeViewSet(mixins.RetrieveModelMixin,
                                  mixins.ListModelMixin,
                                  viewsets.GenericViewSet):
    queryset = BannerSubsectionType.objects.all()
    serializer_class = BannerSubsectionTypeSerializer


class BannerUpdateViewSet(mixins.RetrieveModelMixin,
                          mixins.ListModelMixin,
                          viewsets.GenericViewSet):

    queryset = BannerUpdate.objects.all()
    serializer_class = BannerUpdateSerializer
    filter_backends = (rest_framework.DjangoFilterBackend, SearchFilter,
                       OrderingFilter)
    filter_class = BannerUpdateFilterSet
    pagination_class = BannerUpdatePagination

    @action(detail=False)
    def latest(self, request, *args, **kwargs):
        stores = create_store_filter('view_store_banners')(self.request)\
            .filter_by_banners_support()

        result = {}

        for store in stores:
            store_url = reverse('store-detail', kwargs={'pk': store.pk},
                                request=request)
            store_latest_log = store.bannerupdate_set.order_by(
                '-timestamp')[:1]

            if store_latest_log:
                store_latest_log = BannerUpdateSerializer(
                    store_latest_log[0], context={'request': request}).data
            else:
                store_latest_log = None

            result[store_url] = store_latest_log

        return Response(result)


class BannerAssetViewSet(mixins.RetrieveModelMixin,
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

    @action(methods=['post'], detail=True)
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

    @action(methods=['post'], detail=True)
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
