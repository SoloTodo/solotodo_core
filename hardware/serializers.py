from rest_framework import serializers

from hardware.models import Budget, BudgetEntry
from solotodo.serializers import NestedProductSerializer, UserSerializer


class BudgetEntrySerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = BudgetEntry
        fields = ['id', 'url', 'budget', 'category', 'selected_product',
                  'selected_store']


class BudgetSerializer(serializers.HyperlinkedModelSerializer):
    products_pool = NestedProductSerializer(many=True, required=False,
                                            read_only=True)
    user = UserSerializer(required=False, read_only=True)
    is_public = serializers.BooleanField(required=False, read_only=True)
    entries = BudgetEntrySerializer(many=True, required=False)

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super(BudgetSerializer, self).create(validated_data)

    class Meta:
        model = Budget
        fields = ['id', 'url', 'name', 'creation_date', 'last_updated',
                  'is_public', 'user', 'creation_date', 'products_pool',
                  'entries']
