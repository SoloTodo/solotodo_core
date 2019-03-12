from rest_framework import viewsets, mixins, status
from rest_framework.decorators import detail_route
from rest_framework.response import Response

from django_filters import rest_framework
from rest_framework.filters import SearchFilter, OrderingFilter

from django.db.models import Max
from django.db import IntegrityError

from solotodo.forms.product_form import ProductForm
from .models import ProductList, ProductListEntry
from .serializers import ProductListSerializer, ProductListCreationSerializer
from .filters import ProductListFilterSet
from .pagination import ProductListPagination


class ProductListViewSet(mixins.CreateModelMixin,
                         mixins.RetrieveModelMixin,
                         mixins.ListModelMixin,
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
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

        serializer = ProductListSerializer(
            product_list, context={'request': request})

        return Response(serializer.data)
