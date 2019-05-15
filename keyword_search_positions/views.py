from rest_framework import viewsets, mixins

from .models import KeywordSearch, KeywordSearchUpdate, \
    KeywordSearchEntityPosition
from.serializers import KeywordSearchSerializer


class KeywordSearchViewSet(mixins.RetrieveModelMixin,
                           mixins.ListModelMixin,
                           viewsets.GenericViewSet):
    queryset = KeywordSearch.objects.all()
    serializer_class = KeywordSearchSerializer
