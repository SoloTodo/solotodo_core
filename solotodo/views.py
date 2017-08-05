import json

from django.contrib.auth import get_user_model
from django.contrib.gis.geoip2 import GeoIP2
from django.http import Http404
from geoip2.errors import AddressNotFoundError
from guardian.shortcuts import get_objects_for_user
from rest_framework import viewsets, permissions
from rest_framework.decorators import list_route, detail_route
from rest_framework import exceptions
from rest_framework.response import Response
from rest_framework.reverse import reverse

from solotodo.decorators import detail_permission
from solotodo.drf_extensions import PermissionReadOnlyModelViewSet
from solotodo.forms.ip_form import IpForm
from solotodo.models import Store, Language, Currency, Country, StoreType, \
    ProductType
from solotodo.serializers import UserSerializer, LanguageSerializer, \
    StoreSerializer, CurrencySerializer, CountrySerializer, \
    StoreTypeSerializer, StoreUpdatePricesSerializer, ProductTypeSerializer
from solotodo.tasks import store_update
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


class ProductTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ProductType.objects.all()
    serializer_class = ProductTypeSerializer


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
    queryset = Store.objects.all()
    serializer_class = StoreSerializer

    def get_queryset(self):
        return get_objects_for_user(self.request.user, 'view_store',
                                    klass=Store)

    @detail_route()
    @detail_permission('update_store_prices')
    def scraper(self, request, pk):
        store = self.get_object()
        try:
            store.scraper
        except AttributeError:
            raise Http404
        serializer = StoreUpdatePricesSerializer(
            store, context={'request': request})
        return Response(serializer.data)

    @detail_route(methods=['POST'])
    @detail_permission('update_store_prices')
    def update_prices(self, request, pk):
        store = self.get_object()
        serializer = StoreUpdatePricesSerializer(
            store, data=request.data, context={'request': request})
        if serializer.is_valid():
            validated_data = serializer.validated_data

            product_types = validated_data['product_types']
            if not product_types:
                product_types = None

            queue = validated_data['queue']
            discover_urls_concurrency = \
                validated_data['discover_urls_concurrency']
            products_for_url_concurrency = \
                validated_data['products_for_url_concurrency']
            use_async = validated_data['async']

            task = store_update.delay(
                store.id,
                product_type_ids=[pt.id for pt in product_types],
                extra_args=None, queue=queue,
                discover_urls_concurrency=discover_urls_concurrency,
                products_for_url_concurrency=products_for_url_concurrency,
                use_async=use_async)

            return Response(json.dumps({
                'task_id': task.id
            }))
        else:
            print(serializer.errors)
            return Response(str(serializer.errors))
