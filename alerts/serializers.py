from rest_framework.serializers import HyperlinkedModelSerializer

from alerts.models import Alert
from solotodo.serializers import NestedProductSerializer, \
    EntityHistorySerializer


class AlertSerializer(HyperlinkedModelSerializer):
    product = NestedProductSerializer()
    normal_price_registry = EntityHistorySerializer()
    offer_price_registry = EntityHistorySerializer()

    class Meta:
        model = Alert
        fields = ('id', 'product', 'stores', 'email',
                  'normal_price_registry', 'offer_price_registry',
                  'creation_date', 'last_updated')
