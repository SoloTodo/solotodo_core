from django.db import IntegrityError
from django_filters import rest_framework
from rest_framework import viewsets, status
from rest_framework.decorators import detail_route
from rest_framework.exceptions import PermissionDenied
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.response import Response

from solotodo.drf_extensions import PermissionReadOnlyModelViewSet
from solotodo.forms.category_form import CategoryForm
from wtb.filters import create_wtb_brand_filter, WtbEntityFilterSet, \
    WtbBrandUpdateLogFilterSet
from wtb.forms import WtbEntityAssociationForm
from wtb.models import WtbBrand, WtbEntity, WtbBrandUpdateLog
from wtb.pagination import WtbEntityPagination, WtbStoreUpdateLogPagination
from wtb.serializers import WtbBrandSerializer, WtbEntitySerializer, \
    WtbBrandUpdateLogSerializer, WtbEntityStaffInfoSerializer


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
    ordering_fields = ('name', 'brand', 'last_updated', 'key', 'category',
                       'product')
    search_fields = ('product__instance_model__unicode_representation',
                     'name', 'key', 'url')

    @detail_route()
    def staff_info(self, request, pk):
        wtb_entity = self.get_object()
        if not wtb_entity.user_has_staff_perms(request.user):
            raise PermissionDenied
        serialializer = WtbEntityStaffInfoSerializer(
            wtb_entity, context={'request': request})
        return Response(serialializer.data)

    @detail_route(methods=['post'])
    def toggle_visibility(self, request, *args, **kwargs):
        wtb_entity = self.get_object()
        if not wtb_entity.user_has_staff_perms(request.user):
            raise PermissionDenied

        try:
            wtb_entity.is_visible = not wtb_entity.is_visible
            wtb_entity.save()
            serialized_data = WtbEntitySerializer(
                wtb_entity, context={'request': self.request}).data
            return Response(serialized_data)
        except IntegrityError as err:
            return Response({'detail': str(err)},
                            status=status.HTTP_400_BAD_REQUEST)

    @detail_route(methods=['post'])
    def change_category(self, request, *args, **kwargs):
        wtb_entity = self.get_object()
        if not wtb_entity.user_has_staff_perms(request.user):
            raise PermissionDenied

        if wtb_entity.product:
            return Response({'detail': 'Cannot change category of '
                                       'associated entities'},
                            status=status.HTTP_400_BAD_REQUEST)

        form = CategoryForm(request.data)

        if form.is_valid():
            new_category = form.cleaned_data['category']
            if new_category == wtb_entity.category:
                return Response({'detail': 'The new category must be '
                                           'different from the original one'},
                                status=status.HTTP_400_BAD_REQUEST)

            wtb_entity.category = new_category
            wtb_entity.save()
            serialized_data = WtbEntitySerializer(
                wtb_entity, context={'request': self.request}).data
            return Response(serialized_data)
        else:
            return Response({'detail': form.errors},
                            status=status.HTTP_400_BAD_REQUEST)

    @detail_route(methods=['post'])
    def associate(self, request, *args, **kwargs):
        wtb_entity = self.get_object()
        if not wtb_entity.user_has_staff_perms(request.user):
            raise PermissionDenied

        form = WtbEntityAssociationForm(request.data)
        if not form.is_valid():
            return Response({
                'errors': form.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        product = form.cleaned_data['product']

        try:
            wtb_entity.associate(request.user, product)
        except Exception as ex:
            return Response(
                {'detail': str(ex)},
                status=status.HTTP_400_BAD_REQUEST)

    @detail_route(methods=['post'])
    def dissociate(self, request, *args, **kwargs):
        wtb_entity = self.get_object()
        if not wtb_entity.user_has_staff_perms(request.user):
            raise PermissionDenied

        try:
            wtb_entity.dissociate()
        except Exception as ex:
            return Response(
                {'detail': str(ex)},
                status=status.HTTP_400_BAD_REQUEST)

        serialized_data = WtbEntitySerializer(
            wtb_entity, context={'request': self.request}).data
        return Response(serialized_data)


class WtbBrandUpdateLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = WtbBrandUpdateLog.objects.all()
    serializer_class = WtbBrandUpdateLogSerializer
    pagination_class = WtbStoreUpdateLogPagination
    filter_backends = (rest_framework.DjangoFilterBackend, OrderingFilter)
    filter_class = WtbBrandUpdateLogFilterSet
    ordering_fields = ('last_updated', )
