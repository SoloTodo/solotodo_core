from rest_framework import serializers

from .models import KeywordSearch, KeywordSearchEntityPosition, \
    KeywordSearchUpdate
from solotodo.serializers import StoreSerializer, CategorySerializer


class KeywordSearchSerializer(serializers.HyperlinkedModelSerializer):
    store = StoreSerializer()
    category = CategorySerializer()

    class Meta:
        model = KeywordSearch
        fields = ('id', 'url', 'user', 'store', 'category', 'keyword',
                  'threshold', 'creation_date')


class KeywordSearchUpdateSerializer(serializers.HyperlinkedModelSerializer):
    search = KeywordSearchSerializer()

    class Meta:
        model = KeywordSearchUpdate
        fields = ('search', 'creation_date', 'status', 'message')


class KeywordSearchEntityPositionSerializer(
        serializers.HyperlinkedModelSerializer):
    update = KeywordSearchUpdateSerializer()

    class Meta:
        model = KeywordSearchEntityPosition
        fields = ('entity', 'update', 'value')
