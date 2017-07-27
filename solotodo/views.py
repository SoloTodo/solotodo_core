import json

from guardian.shortcuts import get_objects_for_user
from guardian.utils import get_anonymous_user
from rest_framework import viewsets, permissions
from rest_framework.decorators import list_route
from rest_framework.response import Response

from solotodo.models import Store, Language, Currency, Country
from solotodo.serializers import UserSerializer, LanguageSerializer, \
    StoreSerializer, CurrencySerializer, CountrySerializer


class UserViewSet(viewsets.GenericViewSet):
    permission_classes = (permissions.IsAuthenticated,)

    @list_route(methods=['get', 'patch'])
    def me(self, request):
        user = request.user

        if request.method == 'PATCH':
            content = json.loads(request.body.decode('utf-8'))
            if 'preferred_language' in content:
                language = Language.objects.get(
                    pk=content['preferred_language'])
                user.preferred_language = language
            if 'preferred_currency' in content:
                currency = Currency.objects.get(
                    pk=content['preferred_currency'])
                user.preferred_currency = currency
            user.save()
        return Response(UserSerializer(
            user,
            context={'request': request}).data)


class LanguageViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Language.objects.all()
    serializer_class = LanguageSerializer


class CurrencyViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Currency.objects.all()
    serializer_class = CurrencySerializer


class CountryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Country.objects.all()
    serializer_class = CountrySerializer


class StoreViewSet(viewsets.ReadOnlyModelViewSet):
    def get_queryset(self):
        return get_objects_for_user(self.request.user, 'view_store',
                                    klass=Store)

    queryset = Store.objects.all()
    serializer_class = StoreSerializer
