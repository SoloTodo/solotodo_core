from django_filters import rest_framework
from rest_framework import viewsets

from category_columns.filters import CategoryColumnFilterSet
from category_columns.models import CategoryColumn
from category_columns.serializers import CategoryColumnSerializer


class CategoryColumnViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CategoryColumn.objects.all()
    serializer_class = CategoryColumnSerializer
    filter_backends = (rest_framework.DjangoFilterBackend,)
    filter_class = CategoryColumnFilterSet
