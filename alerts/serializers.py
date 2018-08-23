from guardian.shortcuts import get_objects_for_user
from rest_framework import serializers

from alerts.models import Alert
from solotodo.models import Product, Store, Category
from solotodo.serializers import NestedProductSerializer, \
    EntityHistorySerializer


class AlertSerializer(serializers.HyperlinkedModelSerializer):
    product = NestedProductSerializer()
    normal_price_registry = EntityHistorySerializer()
    offer_price_registry = EntityHistorySerializer()

    class Meta:
        model = Alert
        fields = ('id', 'product', 'stores', 'email',
                  'normal_price_registry', 'offer_price_registry',
                  'creation_date', 'last_updated')


class AlertCreationSerializer(serializers.HyperlinkedModelSerializer):
    product = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all())
    email = serializers.EmailField()
    stores = serializers.PrimaryKeyRelatedField(
        queryset=Store.objects.all(), many=True)

    @property
    def data(self):
        return AlertSerializer(
            self.instance, context={'request': self.context['request']}).data

    def validate_product(self, value):
        user = self.context['request'].user
        valid_categories = get_objects_for_user(user, 'view_category',
                                                klass=Category)

        if value.category not in valid_categories:
            raise serializers.ValidationError('Invalid product')

        return value

    def validate_stores(self, value):
        user = self.context['request'].user

        requested_stores = Store.objects.filter(
            pk__in=[s.pk for s in value])
        valid_stores = get_objects_for_user(user, 'view_store',
                                            klass=requested_stores)

        if len(value) != len(valid_stores):
            raise serializers.ValidationError('Invalid store')

        return value

    def create(self, validated_data):
        return Alert.set_up(validated_data['product'],
                            validated_data['stores'],
                            validated_data['email'])

    class Meta:
        model = Alert
        fields = ('product', 'email', 'stores')
