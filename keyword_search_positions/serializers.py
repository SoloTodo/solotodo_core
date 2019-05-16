from rest_framework import serializers

from .models import KeywordSearch, KeywordSearchEntityPosition, \
    KeywordSearchUpdate
from solotodo.models import Store, Category
from solotodo.serializers import UserSerializer


class KeywordSearchSerializer(serializers.HyperlinkedModelSerializer):
    user = UserSerializer()

    class Meta:
        model = KeywordSearch
        fields = ('id', 'url', 'user', 'store', 'category', 'keyword',
                  'threshold', 'creation_date')


class KeywordSearchCreationSerializer(serializers.HyperlinkedModelSerializer):
    store = serializers.PrimaryKeyRelatedField(
        queryset=Store.objects.all())
    category = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all())
    keyword = serializers.CharField
    threshold = serializers.IntegerField

    @property
    def data(self):
        return KeywordSearchSerializer(
            self.instance, context={'request': self.context['request']}).data

    def validate_category(self, value):
        user = self.context['request'].user

        if not user.has_perm(
                'solotodo.create_category_keyword_search', value):
            raise serializers.ValidationError('Permission denied on category')

        return value

    def validate_store(self, value):
        user = self.context['request'].user

        if not user.has_perm(
                'solotodo.create_store_keyword_search', value):
            raise serializers.ValidationError('Permission denied on store')

        return value

    def create(self, validated_data):
        user = self.context['request'].user
        store = validated_data['store']
        category = validated_data['category']
        keyword = validated_data['keyword']
        threshold = validated_data['threshold']

        keyword_search = KeywordSearch.objects.create(
            user=user,
            store=store,
            category=category,
            keyword=keyword,
            threshold=threshold
        )

        return keyword_search

    class Meta:
        model = KeywordSearch
        fields = ('store', 'category', 'keyword', 'threshold')


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
