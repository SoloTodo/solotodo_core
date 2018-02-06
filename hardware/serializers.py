from rest_framework import serializers

from hardware.models import Budget
from solotodo.serializers import NestedProductSerializer, UserSerializer


class BudgetSerializer(serializers.HyperlinkedModelSerializer):
    products_pool = NestedProductSerializer(many=True, required=False,
                                            read_only=True)
    user = UserSerializer(required=False, read_only=True)
    is_public = serializers.BooleanField(required=False, read_only=True)

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super(BudgetSerializer, self).create(validated_data)

    class Meta:
        model = Budget
        fields = ['id', 'name', 'creation_date', 'is_public', 'user',
                  'creation_date', 'products_pool']
