from rest_framework import viewsets, mixins, status
from rest_framework.decorators import detail_route
from rest_framework.response import Response

from django_filters import rest_framework
from rest_framework.filters import SearchFilter, OrderingFilter

from django.db.models import Max
from django.db import IntegrityError

from solotodo.forms.product_form import ProductForm
from .models import ProductList, ProductListEntry
from .serializers import ProductListSerializer, ProductListCreationSerializer,\
    ProductListUpdateSerializer
from .filters import ProductListFilterSet
from .pagination import ProductListPagination


class ProductListViewSet(mixins.CreateModelMixin,
                         mixins.RetrieveModelMixin,
                         mixins.ListModelMixin,
                         mixins.UpdateModelMixin,
                         mixins.DestroyModelMixin,
                         viewsets.GenericViewSet):
    queryset = ProductList.objects.all()
    serializer_class = ProductListSerializer
    filter_backends = (rest_framework.DjangoFilterBackend, SearchFilter,
                       OrderingFilter)
    filter_class = ProductListFilterSet
    pagination_class = ProductListPagination

    def get_queryset(self):
        user = self.request.user

        if not user.is_authenticated:
            return ProductList.objects.none()
        elif user.is_superuser:
            return ProductList.objects.all()
        else:
            return ProductList.objects.filter(user=user)

    def get_serializer_class(self):
        if self.action == 'create':
            return ProductListCreationSerializer
        elif self.action == 'partial_update':
            return ProductListUpdateSerializer
        else:
            return ProductListSerializer

    @detail_route(methods=['post'])
    def add_product(self, request, pk, *args, **kwargs):
        product_list = self.get_object()
        form = ProductForm.from_category(product_list.category, request.data)

        if not form.is_valid():
            return Response({
                'errors': form.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        product = form.cleaned_data['product']

        ordering = product_list.entries.all().aggregate(Max('ordering'))

        if ordering['ordering__max']:
            ordering = ordering['ordering__max'] + 1
        else:
            ordering = 0

        try:
            ProductListEntry.objects.create(
                product_list=product_list,
                ordering=ordering,
                product=product)
        except IntegrityError as e:
            return Response({
                'errors': {'product': [str(e)]}
            }, status=status.HTTP_400_BAD_REQUEST)

        serializer = ProductListSerializer(
            product_list, context={'request': request})

        return Response(serializer.data)

    @detail_route(methods=['post'])
    def remove_product(self, request, pk, *args, **kwargs):
        product_list = self.get_object()
        form = ProductForm.from_category(product_list.category, request.data)

        if not form.is_valid():
            return Response({
                'errors': form.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        product = form.cleaned_data['product']

        try:
            entry = ProductListEntry.objects.get(
                product_list=product_list,
                product=product)
            entry.delete()
        except ProductListEntry.DoesNotExist as e:
            return Response({
                'errors': {'product': [str(e)]}
            }, status=status.HTTP_400_BAD_REQUEST)

        serializer = ProductListSerializer(
            product_list, context={'request': request}
        )

        return Response(serializer.data)

    @detail_route(methods=['post'])
    def update_entries_ordering(self, request, pk, *args, **kwargs):
        product_list = self.get_object()

        products_ids = request.data.get('products')

        if not isinstance(products_ids, list):
            return Response({
                'errors': {'products': [
                    'Invalid products (no given or not a list)'
                ]}
            }, status=status.HTTP_400_BAD_REQUEST)

        updated_entries = []

        for entry in product_list.entries.all():
            try:
                index = products_ids.index(entry.product.id)
            except ValueError:
                return Response({
                    'errors': {'products': ['"{}" not in list'
                                            .format(entry.product)]}
                }, status=status.HTTP_400_BAD_REQUEST)

            entry.ordering = index
            updated_entries.append(entry)

        for entry in updated_entries:
            entry.save()

        serializer = ProductListSerializer(
            product_list, context={'request': request}
        )

        return Response(serializer.data)
