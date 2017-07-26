from django.contrib.auth import get_user_model
from rest_framework import serializers

from solotodo.models import Language, Store, Currency, Country


class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ('email', 'is_staff', 'is_superuser', 'preferred_language_id',
                  'preferred_country', 'preferred_currency_id')


class LanguageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Language
        fields = ('id', 'code', 'name')


class CurrencySerializer(serializers.ModelSerializer):
    class Meta:
        model = Currency
        fields = ('id', 'name', 'iso_code', 'decimal_places',
                  'decimal_separator', 'thousands_separator', 'prefix',
                  'exchange_rate', 'exchange_rate_last_updated')


class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = ('id', 'name', 'currency_id')


class StoreSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Store
        fields = ('id', 'name')
