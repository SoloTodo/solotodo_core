from guardian.shortcuts import get_objects_for_user
from rest_framework import serializers

from .models import Alert, AnonymousAlert
from solotodo.models import Product, Store, Category
from solotodo.serializers import NestedProductSerializer, \
    EntityHistorySerializer


class AlertSerializer(serializers.HyperlinkedModelSerializer):
    product = NestedProductSerializer()
    normal_price_registry = EntityHistorySerializer()
    offer_price_registry = EntityHistorySerializer()

    class Meta:
        model = Alert
        fields = ('id', 'product', 'stores',
                  'normal_price_registry', 'offer_price_registry',
                  'creation_date', 'last_updated')


class AnonymousAlertSerializer(serializers.HyperlinkedModelSerializer):
    alert = AlertSerializer()

    class Meta:
        model = AnonymousAlert
        fields = ('id', 'alert', 'email')


class AnonymousAlertCreationSerializer(serializers.HyperlinkedModelSerializer):
    product = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all())
    email = serializers.EmailField()
    stores = serializers.PrimaryKeyRelatedField(
        queryset=Store.objects.all(), many=True)

    @property
    def data(self):
        return AnonymousAlertSerializer(
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

    def validate(self, attrs):
        if AnonymousAlert.objects.filter(email=attrs['email'],
                                         alert__product=attrs['product']):
            raise serializers.ValidationError(
                'email/product combination not unique')

        return attrs

    def create(self, validated_data):
        alert = Alert.set_up(validated_data['product'],
                             validated_data['stores'])
        return AnonymousAlert.objects.create(alert=alert,
                                             email=validated_data['email'])

    class Meta:
        model = AnonymousAlert
        fields = ('product', 'email', 'stores')
