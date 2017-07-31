from django.contrib.auth import get_user_model
from rest_framework import serializers

from solotodo.models import Language, Store, Currency, Country, StoreType


class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ('url', 'email', 'first_name', 'last_name',
                  'preferred_language', 'preferred_country',
                  'preferred_currency', 'permissions')
        read_only_fields = ('email', 'first_name', 'last_name',
                            'permissions')


class StoreTypeSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = StoreType
        fields = ('url', 'name')


class LanguageSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Language
        fields = ('url', 'code', 'name')


class CurrencySerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Currency
        fields = ('url', 'name', 'iso_code', 'decimal_places',
                  'decimal_separator', 'thousands_separator', 'prefix',
                  'exchange_rate', 'exchange_rate_last_updated')


class CountrySerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Country
        fields = ('url', 'name', 'currency')


class StoreSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Store
        fields = ('url', 'id', 'name', 'country', 'is_active', 'type',
                  'storescraper_class')
