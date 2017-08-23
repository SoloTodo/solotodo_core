import traceback

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.gis.geoip2 import GeoIP2
from django.core.mail import send_mail
from django.http import Http404
from django.template.loader import render_to_string
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from geoip2.errors import AddressNotFoundError
from guardian.shortcuts import get_objects_for_user
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import list_route, detail_route
from rest_framework import exceptions
from rest_framework.exceptions import PermissionDenied
from rest_framework.filters import OrderingFilter, \
    SearchFilter
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from rest_framework.reverse import reverse

from solotodo.decorators import detail_permission
from solotodo.drf_extensions import PermissionReadOnlyModelViewSet
from solotodo.filters import EntityFilterSet, StoreUpdateLogFilterSet, \
    ProductFilterSet
from solotodo.forms.ip_form import IpForm
from solotodo.models import Store, Language, Currency, Country, StoreType, \
    ProductType, StoreUpdateLog, Entity, Product, NumberFormat, SoloTodoUser
from solotodo.pagination import StoreUpdateLogPagination, EntityPagination, \
    ProductPagination
from solotodo.serializers import UserSerializer, LanguageSerializer, \
    StoreSerializer, CurrencySerializer, CountrySerializer, \
    StoreTypeSerializer, StoreUpdatePricesSerializer, ProductTypeSerializer, \
    StoreUpdateLogSerializer, EntitySerializer, ProductSerializer, \
    NumberFormatSerializer
from solotodo.tasks import store_update
from solotodo.utils import get_client_ip
from storescraper.store import StoreScrapError


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = get_user_model().objects.all()
    serializer_class = UserSerializer
    permission_classes = (permissions.IsAdminUser,)

    @list_route(methods=['get', 'patch'],
                permission_classes=(permissions.IsAuthenticated, ))
    def me(self, request):
        user = request.user

        if request.method == 'PATCH':
            content = JSONParser().parse(request)
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


class NumberFormatViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = NumberFormat.objects.all()
    serializer_class = NumberFormatSerializer


class StoreTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = StoreType.objects.all()
    serializer_class = StoreTypeSerializer


class CurrencyViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Currency.objects.all()
    serializer_class = CurrencySerializer


class ProductTypeViewSet(PermissionReadOnlyModelViewSet):
    queryset = ProductType.objects.all()
    serializer_class = ProductTypeSerializer


class CountryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Country.objects.all()
    serializer_class = CountrySerializer

    @list_route()
    def by_ip(self, request):
        if 'ip' in request.query_params:
            form = IpForm(request.query_params)
        else:
            form = IpForm({'ip': get_client_ip(request)})

        if form.is_valid():
            geo_ip2 = GeoIP2()
            try:
                country_data = geo_ip2.country(form.cleaned_data['ip'])
            except AddressNotFoundError as err:
                raise exceptions.NotFound(err)
            try:
                country = Country.objects.get(
                    iso_code=country_data['country_code'])
            except Country.DoesNotExist as err:
                raise exceptions.NotFound(err)
        else:
            raise exceptions.ValidationError({'detail': 'Invalid IP address'})

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

    @detail_route(methods=['post'])
    @detail_permission('update_store_prices')
    def update_pricing(self, request, pk):
        store = self.get_object()
        serializer = StoreUpdatePricesSerializer(
            store, data=request.data, context={'request': request})

        if serializer.is_valid():
            validated_data = serializer.validated_data

            product_types = validated_data['product_types']
            if product_types:
                product_types_ids = [pt.id for pt in product_types]
            else:
                product_types_ids = None

            queue = validated_data.get('queue')
            discover_urls_concurrency = \
                validated_data.get('discover_urls_concurrency')
            products_for_url_concurrency = \
                validated_data.get('products_for_url_concurrency')
            use_async = validated_data.get('async')

            store_update_log = StoreUpdateLog.objects.create(store=store)

            task = store_update.delay(
                store.id,
                product_type_ids=product_types_ids,
                extra_args=None, queue=queue,
                discover_urls_concurrency=discover_urls_concurrency,
                products_for_url_concurrency=products_for_url_concurrency,
                use_async=use_async,
                update_log_id=store_update_log.id
            )

            return Response({
                'task_id': task.id,
                'log_id': store_update_log.id
            })
        else:
            return Response(serializer.errors)


class StoreUpdateLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = StoreUpdateLog.objects.all()
    serializer_class = StoreUpdateLogSerializer
    pagination_class = StoreUpdateLogPagination
    filter_backends = (DjangoFilterBackend, OrderingFilter)
    filter_class = StoreUpdateLogFilterSet
    ordering_fields = ('last_updated', )

    @list_route()
    def latest(self, request, *args, **kwargs):
        stores = get_objects_for_user(
            self.request.user, 'view_store_update_logs', klass=Store)

        result = {}

        for store in stores:
            store_url = reverse('store-detail', kwargs={'pk': store.pk},
                                request=request)
            store_latest_log = store.storeupdatelog_set.order_by(
                '-last_updated')[:1]

            if store_latest_log:
                store_latest_log = StoreUpdateLogSerializer(
                    store_latest_log[0], context={'request': request}).data
            else:
                store_latest_log = None

            result[store_url] = store_latest_log

        return Response(result)


class EntityViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Entity.objects.all()
    serializer_class = EntitySerializer
    pagination_class = EntityPagination
    filter_backends = (DjangoFilterBackend, SearchFilter)
    filter_class = EntityFilterSet
    search_fields = ('product__instance_model__unicode_representation',
                     'cell_plan__instance_model__unicode_representation',
                     'name',
                     'cell_plan_name',
                     'part_number',
                     'sku',
                     'key',
                     'url',
                     'discovery_url')

    @detail_route(methods=['post'])
    def update_pricing(self, request, *args, **kwargs):
        entity = self.get_object()
        user = request.user

        has_perm = user.has_perm('update_store_prices', entity.store) \
            or user.has_perm('associate_product_type_entities',
                             entity.product_type) \
            or user.has_perm('update_product_type_entities_prices',
                             entity.product_type)

        if not has_perm:
            raise PermissionDenied

        try:
            entity.update()
            serializer = EntitySerializer(entity, context={'request': request})
            return Response(serializer.data)
        except Exception as e:
            html_message = render_to_string('mailing/index.html', {
                'entity': entity,
                'request_user': user,
                'timestamp': timezone.now(),
                'host': settings.BACKEND_HOST,
                'error': traceback.format_exc()
            })

            sender = get_user_model().get_bot().email_recipient_text()
            recipients = [u.email for u in get_user_model().objects.filter(
                is_superuser=True)]

            send_mail('Error actualizando entidad {}'.format(entity.id),
                      'Error', sender, recipients,
                      html_message=html_message)

            return Response({'detail': str(e)},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filter_backends = (DjangoFilterBackend, SearchFilter)
    filter_class = ProductFilterSet
    pagination_class = ProductPagination
