from rest_framework import serializers

from .models import ProductList, ProductListEntry
from solotodo.models import Category
from solotodo.serializers import ProductSerializer


class ProductListEntrySerializer(serializers.HyperlinkedModelSerializer):
    product = ProductSerializer()

    class Meta:
        model = ProductListEntry
        fields = ('product', 'ordering')


class ProductListSerializer(serializers.HyperlinkedModelSerializer):
    entries = ProductListEntrySerializer(many=True)

    class Meta:
        model = ProductList
        fields = ('url', 'id', 'name', 'category', 'entries',
                  'creation_date', 'last_updated')


class ProductListCreationSerializer(serializers.HyperlinkedModelSerializer):
    name = serializers.CharField()
    category = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all())

    @property
    def data(self):
        return ProductListSerializer(
            self.instance, context={'request': self.context['request']}).data

    def validate_category(self, value):
        user = self.context['request'].user

        if not user.has_perm('solotodo.create_category_product_list', value):
            raise serializers.ValidationError('Permission denied on category')

        return value

    def create(self, validated_data):
        user = self.context['request'].user
        name = validated_data['name']
        category = validated_data['category']

        return ProductList.objects.create(
            user=user,
            name=name,
            category=category
        )

    class Meta:
        model = ProductList
        fields = ('name', 'category')
