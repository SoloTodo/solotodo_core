from rest_framework import serializers

from .models import StoreSubscription


class StoreSubscriptionSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = StoreSubscription
        fields = ('id', 'url', 'user', 'store', 'categories', 'creation_date')
