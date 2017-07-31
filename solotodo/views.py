import json

from django.contrib.auth import get_user_model
from django.contrib.gis.geoip2 import GeoIP2
from geoip2.errors import AddressNotFoundError
from guardian.shortcuts import get_objects_for_user
from rest_framework import viewsets, permissions
from rest_framework.decorators import list_route
from rest_framework import exceptions
from rest_framework.response import Response
from rest_framework.reverse import reverse

from solotodo.drf_extensions import PermissionReadOnlyModelViewSet
from solotodo.forms.ip_form import IpForm
from solotodo.models import Store, Language, Currency, Country, StoreType
from solotodo.serializers import UserSerializer, LanguageSerializer, \
    StoreSerializer, CurrencySerializer, CountrySerializer, StoreTypeSerializer
from solotodo.utils import get_client_ip


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = get_user_model().objects.all()
    permission_classes = (permissions.IsAdminUser,)

    @list_route(methods=['get', 'patch'],
                permission_classes=(permissions.IsAuthenticated, ))
    def me(self, request):
        user = request.user

        if request.method == 'PATCH':
            content = json.loads(request.body.decode('utf-8'))
            serializer = UserSerializer(
                user, data=content, partial=True,
                context={'request': request})
            if serializer.is_valid(raise_exception=True):
                serializer.save()

        payload = UserSerializer(
            user,
            context={'request': request}).data

        payload['url'] = reverse('solotodouser-me', request=request)
        return Response(payload)


class LanguageViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Language.objects.all()
    serializer_class = LanguageSerializer


class StoreTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = StoreType.objects.all()
    serializer_class = StoreTypeSerializer


class CurrencyViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Currency.objects.all()
    serializer_class = CurrencySerializer


class CountryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Country.objects.all()
    serializer_class = CountrySerializer

    @list_route()
    def by_ip(self, request):
        if 'ip' in request.GET:
            form = IpForm(request.GET)
        else:
            form = IpForm({'ip': get_client_ip(request)})

        if form.is_valid():
            geo_ip2 = GeoIP2()
            try:
                country_data = geo_ip2.country(form.cleaned_data['ip'])
            except AddressNotFoundError as err:
                raise exceptions.NotFound(str(err))
            try:
                country = Country.objects.get(
                    iso_code=country_data['country_code'])
            except Country.DoesNotExist as err:
                raise exceptions.NotFound(str(err))
        else:
            raise exceptions.ValidationError('Invalid IP address')

        serializer = CountrySerializer(
            country,
            context={'request': request})
        return Response(serializer.data)


class StoreViewSet(PermissionReadOnlyModelViewSet):
    def get_queryset(self):
        return get_objects_for_user(self.request.user, 'view_store',
                                    klass=Store)

    queryset = Store.objects.all()
    serializer_class = StoreSerializer
