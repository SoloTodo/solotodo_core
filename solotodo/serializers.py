from django.contrib.auth import get_user_model
from rest_framework import serializers

from solotodo.models import Language, Store


class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ('email', 'is_staff', 'is_superuser', 'preferred_language_id',
                  'preferred_country', 'preferred_currency')


class LanguageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Language
        fields = ('id', 'code', 'name')


class StoreSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Store
        fields = ('id', 'name')
