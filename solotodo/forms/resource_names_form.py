from django import forms

from solotodo.models import Country, Currency, StoreType, Store, NumberFormat
from solotodo.serializers import CountrySerializer, CurrencySerializer, \
    StoreTypeSerializer, StoreSerializer, NumberFormatSerializer


class ResourceNamesForm(forms.Form):
    model_map = {
        'countries': {
            'model': Country,
            'serializer': CountrySerializer,
            'permission': None
        },
        'currencies': {
            'model': Currency,
            'serializer': CurrencySerializer,
            'permission': None
        },
        'store_types': {
            'model': StoreType,
            'serializer': StoreTypeSerializer,
            'permission': None
        },
        'stores': {
            'model': Store,
            'serializer': StoreSerializer,
            'permission': 'view_store'
        },
        'number_formats': {
            'model': NumberFormat,
            'serializer': NumberFormatSerializer,
            'permission': None
        }
    }

    choices = [(key, key) for key in model_map.keys()]

    names = forms.MultipleChoiceField(
        choices=choices,
        required=False
    )
