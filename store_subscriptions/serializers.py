from rest_framework import serializers
from guardian.shortcuts import get_objects_for_user

from .models import StoreSubscription
from solotodo.models import Store, Category


class StoreSubscriptionSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = StoreSubscription
        fields = ('id', 'url', 'user', 'store', 'categories', 'creation_date')


class StoreSubscriptionCreationSerializer(
        serializers.HyperlinkedModelSerializer):
    store = serializers.PrimaryKeyRelatedField(
        queryset=Store.objects.all(), required=True)
    categories = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), many=True)

    @property
    def data(self):
        return StoreSubscriptionSerializer(
            self.instance, context={'request':self.context['request']}).data

    def validate_store(self, value):
        user = self.context['request'].user
        valid_stores = get_objects_for_user(
            user, 'view_store', klass=Store)

        if value not in valid_stores:
            raise serializers.ValidationError('Invalid product')

        return value

    def validate_categories(self, value):
        user = self.context['request'].user

        requested_categories = Category.objects.filter(
            pk__in=[c.pk for c in value])
        valid_categories = get_objects_for_user(
            user, 'view_category', klass=requested_categories)

        if len(value) != len(valid_categories):
            raise serializers.ValidationError('Invalid category')

        return value

    def create(self, validated_data):
        user = self.context['request'].user
        store = validated_data['store']
        categories = validated_data['categories']

        store_subscription = StoreSubscription.objects.create(
            user=user, store=store)
        store_subscription.categories.set(categories)
        store_subscription.save()

        return store_subscription

    class Meta:
        model = StoreSubscription
        fields = ('store', 'categories')
