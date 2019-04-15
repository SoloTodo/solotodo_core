from rest_framework import viewsets, mixins
from django_filters import rest_framework

from .models import EntityPosition, EntityPositionSection
from .serializers import EntityPositionSerializer, \
    EntityPositionSectionSerializer
from .pagination import EntityPositionPagination
from .filters import EntityPositionFilterSet


class EntityPositionViewSet(mixins.CreateModelMixin,
                            mixins.RetrieveModelMixin,
                            mixins.ListModelMixin,
                            viewsets.GenericViewSet):
    queryset = EntityPosition.objects.all()
    serializer_class = EntityPositionSerializer
    filter_backends = (rest_framework.DjangoFilterBackend,)
    filter_class = EntityPositionFilterSet
    pagination_class = EntityPositionPagination


class EntityPositionSectionViewSet(mixins.CreateModelMixin,
                                   mixins.RetrieveModelMixin,
                                   mixins.ListModelMixin,
                                   viewsets.GenericViewSet):
    queryset = EntityPositionSection.objects.all()
    serializer_class = EntityPositionSectionSerializer
