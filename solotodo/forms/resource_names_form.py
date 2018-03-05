from django import forms

from category_templates.models import CategoryTemplate
from category_templates.serializers import CategoryTemplateSerializer
from solotodo.models import Country, Currency, StoreType, Store, \
    NumberFormat, Category
from solotodo.serializers import CountrySerializer, CurrencySerializer, \
    StoreTypeSerializer, StoreSerializer, NumberFormatSerializer, \
    CategorySerializer


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
        },
        'categories': {
            'model': Category,
            'serializer': CategorySerializer,
            'permission': 'view_category'
        },
        'category_templates': {
            'model': CategoryTemplate,
            'serializer': CategoryTemplateSerializer,
            'permission': None
        }
    }

    choices = [(key, key) for key in model_map.keys()]

    names = forms.MultipleChoiceField(
        choices=choices,
        required=False
    )
