from rest_framework import viewsets, mixins

from .models import KeywordSearch, KeywordSearchUpdate, \
    KeywordSearchEntityPosition
from.serializers import KeywordSearchSerializer, \
    KeywordSearchUpdateSerializer, KeywordSearchCreationSerializer


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

    def get_queryset(self):
        user = self.request.user

        if not user.is_authenticated:
            return KeywordSearchUpdate.objects.none()
        elif user.is_superuser:
            return KeywordSearchUpdate.objects.all()
        else:
            return KeywordSearchUpdate.objects.filter(search__user=user)
