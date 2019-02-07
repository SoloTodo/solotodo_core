from guardian.shortcuts import get_objects_for_user
from rest_framework import serializers

from .models import Alert, AnonymousAlert, UserAlert
from solotodo.models import Product, Store, Category, Entity
from solotodo.serializers import UserSerializer, EntitySerializer
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


class UserAlertSerializer(serializers.HyperlinkedModelSerializer):
    alert = AlertSerializer()
    entity = EntitySerializer(required=False)
    user = UserSerializer()

    class Meta:
        model = UserAlert
        fields = ('id', 'alert', 'entity', 'user')


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
        product = validated_data['product']
        stores = validated_data['stores']

        normal_price_registry = Alert.find_optimum_entity_history(
            product, stores, 'normal')
        offer_price_registry = Alert.find_optimum_entity_history(
            product, stores, 'offer')

        alert = Alert.objects.create(
            product=product,
            normal_price_registry=normal_price_registry,
            offer_price_registry=offer_price_registry
        )

        return AnonymousAlert.objects.create(alert=alert,
                                             email=validated_data['email'])

    class Meta:
        model = AnonymousAlert
        fields = ('product', 'email', 'stores')


class UserAlertCreationSerializer(serializers.HyperlinkedModelSerializer):
    product = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(), required=False)
    entity = serializers.PrimaryKeyRelatedField(
        queryset=Entity.objects.all(), required=False)
    stores = serializers.PrimaryKeyRelatedField(
        queryset=Store.objects.all(), many=True)

    @property
    def data(self):
        return UserAlertSerializer(
            self.instance, context={'request': self.context['request']}).data

    def validate_product(self, value):
        user = self.context['request'].user
        valid_categories = get_objects_for_user(user, 'view_category',
                                                klass=Category)

        if value.category not in valid_categories:
            raise serializers.ValidationError('Invalid product')

        return value

    def validate_entity(self, value):
        user = self.context['request'].user
        valid_categories = get_objects_for_user(user, 'view_category',
                                                klass=Category)

        if value.category not in valid_categories:
            raise serializers.ValidationError('Invalid entity')

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
        if attrs['entity'] and attrs['product']:
            raise serializers.ValidationError(
                'alert has both a product and an entity'
                '(only one should be defined)')

        if not attrs['entity'] and not attrs['product']:
            raise serializers.ValidationError(
                'alert does not have a product nor an entity')

        return attrs

    def create(self, validated_data):
        user = self.context['request'].user
        product = validated_data['product']
        entity = validated_data['entity']
        stores = validated_data['stores']

        if product:
            normal_price_registry = Alert.find_optimum_entity_history(
                product, stores, 'normal')
            offer_price_registry = Alert.find_optimum_entity_history(
                product, stores, 'offer')
        else:
            normal_price_registry = entity.active_registry
            offer_price_registry = entity.active_registry

        alert = Alert.objects.create(
            product=product,
            normal_price_registry=normal_price_registry,
            offer_price_registry=offer_price_registry
        )

        return UserAlert.objects.create(alert=alert, user=user, entity=entity)

    class Meta:
        model = UserAlert
        fields = ('product', 'entity', 'stores')
