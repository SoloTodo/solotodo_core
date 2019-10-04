from guardian.shortcuts import get_objects_for_user
from rest_framework import serializers

from .models import ProductPriceAlert, ProductPriceAlertHistory
from solotodo.models import Product, Store, Category
from solotodo.serializers import UserSerializer
from solotodo.serializers import NestedProductSerializer


class ProductPriceAlertSerializer(serializers.HyperlinkedModelSerializer):
    user = UserSerializer()
    product = NestedProductSerializer()

    class Meta:
        model = ProductPriceAlert
        fields = ('id', 'url', 'product', 'stores', 'user', 'email',
                  'creation_date')


class ProductPriceAlertCreationSerializer(
        serializers.HyperlinkedModelSerializer):
    product = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(), required=True)
    stores = serializers.PrimaryKeyRelatedField(
        queryset=Store.objects.all(), many=True)
    email = serializers.CharField(required=False)

    @property
    def data(self):
        return ProductPriceAlertSerializer(
            self.instance, context={'request': self.context['request']}).data

    def validate_product(self, value):
        user = self.context['request'].user
        email = self.context['request'].data.get('email')

        if not email:
            valid_categories = get_objects_for_user(
                user, 'view_category_reports', klass=Category)
        else:
            valid_categories = get_objects_for_user(
                user, 'view_category', klass=Category)

        if value.category not in valid_categories:
            raise serializers.ValidationError('Invalid product')

        return value

    def validate_stores(self, value):
        user = self.context['request'].user
        email = self.context['request'].data.get('email')

        if not email:
            requested_stores = Store.objects.filter(
                pk__in=[s.pk for s in value])
            valid_stores = get_objects_for_user(
                user, 'view_store_reports', klass=requested_stores)
        else:
            requested_stores = Store.objects.filter(
                pk__in=[s.pk for s in value])
            valid_stores = get_objects_for_user(
                user, 'view_store', klass=requested_stores)

        if len(value) != len(valid_stores):
            raise serializers.ValidationError('Invalid store')

        return value

    def validate(self, attrs):
        product = attrs.get('product')
        email = self.context['request'].data.get('email')

        if not product:
            raise serializers.ValidationError(
                'Alert does not have a product')

        if email:
            if ProductPriceAlert.objects.filter(email=email, product=product):
                raise serializers.ValidationError(
                    'email/product combination not unique')

        return attrs

    def create(self, validated_data):
        user = self.context['request'].user
        stores = validated_data['stores']
        product = validated_data['product']
        email = validated_data.get('email', None)

        if email:

            alert = ProductPriceAlert.objects.create(
                product=product,
                email=email)
        else:
            alert = ProductPriceAlert.objects.create(
                product=product,
                user=user)

        alert.stores.set(stores)
        alert.update_active_history()

        return alert

    class Meta:
        model = ProductPriceAlert
        fields = ('product', 'stores', 'email')


class ProductPriceAlertHistorySerializer(
        serializers.HyperlinkedModelSerializer):

    class Meta:
        model = ProductPriceAlertHistory
        fields = ('id', 'url', 'alert', 'entries', 'timestamp')
