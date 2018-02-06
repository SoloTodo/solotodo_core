from rest_framework import serializers

from hardware.models import Budget


class InlineBudgetSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Budget
        fields = ['id', 'name', 'creation_date']
