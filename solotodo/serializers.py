from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.fields import empty

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


class StoreUpdatePricesSerializer(serializers.Serializer):
    discover_urls_concurrency = serializers.IntegerField()
    products_for_url_concurrency = serializers.IntegerField()
    queue = serializers.ChoiceField(choices=[
        ('us', 'United States'),
        ('cl', 'Chile')
    ])
    async = serializers.BooleanField(required=False)
    product_types = serializers.ChoiceField(choices=[], required=False)

    def __init__(self, store, data=empty):
        super(StoreUpdatePricesSerializer, self).__init__(None, data)
        scraper = store.scraper
        self.fields['discover_urls_concurrency'].initial = \
            scraper.preferred_discover_urls_concurrency
        self.fields['products_for_url_concurrency'].initial = \
            scraper.preferred_products_for_url_concurrency
        self.fields['queue'].initial = scraper.preferred_queue
        self.fields['async'].initial = scraper.prefer_async
        self.fields['product_types'].choices = [
            (pt.id, str(pt)) for pt in store.scraper_product_types()
        ]
        self.fields['product_types'].initial = [
            (pt.id, str(pt)) for pt in store.scraper_product_types()
        ]
