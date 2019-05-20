from django_filters import rest_framework

from rest_framework import viewsets, mixins
from rest_framework.response import Response

from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.decorators import list_route, detail_route

from .models import KeywordSearch, KeywordSearchUpdate, \
    KeywordSearchEntityPosition
from .pagination import KeywordSearchUpdatePagination
from .serializers import KeywordSearchSerializer, \
    KeywordSearchUpdateSerializer, KeywordSearchCreationSerializer, \
    KeywordSearchEntityPositionSerializer
from .filters import KeywordSearchUpdateFilterSet


class KeywordSearchViewSet(mixins.RetrieveModelMixin,
                           mixins.ListModelMixin,
                           mixins.CreateModelMixin,
                           viewsets.GenericViewSet):
    queryset = KeywordSearch.objects.all()
    serializer_class = KeywordSearchSerializer

    def get_queryset(self):
        user = self.request.user

        if not user.is_authenticated:
            return KeywordSearch.objects.none()
        elif user.is_superuser:
            return KeywordSearch.objects.all()
        else:
            return KeywordSearch.objects.filter(user=user)

    def get_serializer_class(self):
        if self.action == 'create':
            return KeywordSearchCreationSerializer
        else:
            return KeywordSearchSerializer


class KeywordSearchUpdateViewSet(mixins.RetrieveModelMixin,
                                 mixins.ListModelMixin,
                                 viewsets.GenericViewSet):
    queryset = KeywordSearchUpdate.objects.all()
    serializer_class = KeywordSearchUpdateSerializer
    filter_backends = (rest_framework.DjangoFilterBackend, SearchFilter,
                       OrderingFilter)
    filter_class = KeywordSearchUpdateFilterSet
    pagination_class = KeywordSearchUpdatePagination

    def get_queryset(self):
        user = self.request.user

        if not user.is_authenticated:
            return KeywordSearchUpdate.objects.none()
        elif user.is_superuser:
            return KeywordSearchUpdate.objects.all()
        else:
            return KeywordSearchUpdate.objects.filter(search__user=user)

    @detail_route()
    def positions(self, request, pk):
        update = self.get_object()
        positions = update.positions.all().select_related('entity')
        serializer = KeywordSearchEntityPositionSerializer(
            positions, many=True, context={'request': request})

        return Response(serializer.data)


class KeywordSearchEntityPositionViewSet(mixins.RetrieveModelMixin,
                                         mixins.ListModelMixin,
                                         viewsets.GenericViewSet):
    queryset = KeywordSearchEntityPosition.objects.all()
    serializer_class = KeywordSearchEntityPositionSerializer
    pagination_class = KeywordSearchUpdatePagination

    def get_queryset(self):
        user = self.request.user

        if not user.is_authenticated:
            return KeywordSearchEntityPosition.objects.none()
        elif user.is_superuser:
            return KeywordSearchEntityPosition.objects.all()
        else:
            return KeywordSearchEntityPosition.objects.filter(
                update__search__user=user)
