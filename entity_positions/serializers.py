from rest_framework import serializers

from .models import EntityPosition, EntityPositionSection
from solotodo.serializers import EntityHistorySerializer


class EntityPositionSectionSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = EntityPositionSection
        fields = ('id', 'url', 'name', 'store')


class EntityPositionSerializer(serializers.HyperlinkedModelSerializer):
    entity_history = EntityHistorySerializer()
    section = EntityPositionSectionSerializer

    class Meta:
        model = EntityPosition
        fields = ('id', 'url', 'value', 'entity_history', 'section')
