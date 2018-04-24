import hashlib
import json
import traceback
from collections import OrderedDict

import datetime

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.gis.geoip2 import GeoIP2
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import models, IntegrityError
from django.db.models import Avg, Count
from django.http import Http404
from django.utils import timezone
from django_filters import rest_framework
from geoip2.errors import AddressNotFoundError
from guardian.shortcuts import get_objects_for_user
from guardian.utils import get_anonymous_user
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import list_route, detail_route
from rest_framework import exceptions
from rest_framework.exceptions import PermissionDenied
from rest_framework.filters import OrderingFilter, \
    SearchFilter
from rest_framework.generics import get_object_or_404
from rest_framework.parsers import JSONParser
from rest_framework.permissions import DjangoModelPermissionsOrAnonReadOnly
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.reverse import reverse
from sorl.thumbnail import get_thumbnail

from navigation.models import NavDepartment
from navigation.serializers import NavDepartmentSerializer
from solotodo.decorators import detail_permission
from solotodo.drf_custom_ordering import CustomProductOrderingFilter, \
    CustomEntityOrderingFilter
from solotodo.drf_extensions import PermissionReadOnlyModelViewSet
from solotodo.filter_querysets import create_category_filter, \
    create_store_filter
from solotodo.filters import EntityFilterSet, StoreUpdateLogFilterSet, \
    ProductFilterSet, UserFilterSet, EntityHistoryFilterSet, StoreFilterSet, \
    LeadFilterSet, EntityEstimatedSalesFilterSet, EntityStaffFilterSet, \
    WebsiteFilterSet, VisitFilterSet, RatingFilterSet
from solotodo.forms.date_range_form import DateRangeForm
from solotodo.forms.entity_association_form import EntityAssociationForm
from solotodo.forms.entity_by_url_form import EntityByUrlForm
from solotodo.forms.entity_dissociation_form import EntityDisssociationForm
from solotodo.forms.entity_estimated_sales_form import EntityEstimatedSalesForm
from solotodo.forms.lead_grouping_form import LeadGroupingForm
from solotodo.forms.ip_form import IpForm
from solotodo.forms.category_form import CategoryForm
from solotodo.forms.product_bucket_fields_form import ProductBucketFieldForm
from solotodo.forms.product_picture_form import ProductPictureForm
from solotodo.forms.products_browse_form import ProductsBrowseForm
from solotodo.forms.resource_names_form import ResourceNamesForm
from solotodo.forms.website_form import WebsiteForm
from solotodo.forms.store_update_pricing_form import StoreUpdatePricingForm
from solotodo.forms.visit_grouping_form import VisitGroupingForm
from solotodo.models import Store, Language, Currency, Country, StoreType, \
    Category, StoreUpdateLog, Entity, Product, NumberFormat, Website, Lead, \
    EntityHistory, Visit, Rating
from solotodo.pagination import StoreUpdateLogPagination, EntityPagination, \
    ProductPagination, UserPagination, LeadPagination, \
    EntitySalesEstimatePagination, EntityHistoryPagination, VisitPagination, \
    RatingPagination
from solotodo.permissions import RatingPermission
from solotodo.serializers import UserSerializer, LanguageSerializer, \
    StoreSerializer, CurrencySerializer, CountrySerializer, \
    StoreTypeSerializer, StoreScraperSerializer, CategorySerializer, \
    StoreUpdateLogSerializer, EntitySerializer, ProductSerializer, \
    NumberFormatSerializer, EntityEventUserSerializer, \
    EntityEventValueSerializer, MyUserSerializer, \
    EntityHistoryWithStockSerializer, \
    WebsiteSerializer, LeadSerializer, EntityConflictSerializer, \
    LeadWithUserDataSerializer, CategorySpecsFilterSerializer, \
    CategorySpecsOrderSerializer, EntityHistorySerializer, \
    EntityStaffInfoSerializer, VisitSerializer, VisitWithUserDataSerializer, \
    ProductPricingHistorySerializer, NestedProductSerializer, \
    ProductAvailableEntitiesSerializer, RatingSerializer, \
    RatingFullSerializer, StoreRatingSerializer, RatingCreateSerializer
from solotodo.tasks import store_update
from solotodo.utils import get_client_ip, iterable_to_dict, generate_cache_key
from rest_framework_tracking.mixins import LoggingMixin


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = get_user_model().objects.all()
    serializer_class = UserSerializer
    pagination_class = UserPagination
    filter_backends = (rest_framework.DjangoFilterBackend, OrderingFilter)
    filter_class = UserFilterSet

    @list_route(methods=['get', 'patch'],
                permission_classes=(permissions.IsAuthenticated, ))
    def me(self, request):
        user = request.user

        if request.method == 'PATCH':
            content = JSONParser().parse(request)
            serializer = MyUserSerializer(
                user, data=content, partial=True,
                context={'request': request})
            if serializer.is_valid(raise_exception=True):
                serializer.save()

        payload = MyUserSerializer(
            user,
            context={'request': request}).data

        payload['url'] = reverse('solotodouser-me', request=request)
        return Response(payload)

    @list_route()
    def with_staff_actions(self, request):
        users = self.get_queryset()
        users_with_staff_actions = users.filter_with_staff_actions()
        payload = UserSerializer(users_with_staff_actions,
                                 many=True, context={'request': request})
        return Response(payload.data)

    @detail_route()
    def staff_summary(self, request, pk, *args, **kwargs):
        request_user = request.user

        if not request_user.is_authenticated:
            raise PermissionDenied

        user = self.get_object()

        if user != request_user and not request_user.is_superuser:
            raise PermissionDenied

        if not user.is_staff:
            raise Http404

        form = DateRangeForm(request.query_params)

        end_date = timezone.now()
        start_date = end_date - datetime.timedelta(days=30)

        if form.is_valid():
            form_dates = form.cleaned_data['timestamp']
            if form_dates and form_dates.start and form_dates.stop:
                start_date = form_dates.start
                end_date = form_dates.stop
        else:
            return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)

        result = user.staff_summary(start_date, end_date)

        return Response(result)

    @detail_route()
    def staff_actions(self, request, pk, *args, **kwargs):

        request_user = request.user

        if not request_user.is_authenticated:
            raise PermissionDenied

        user = self.get_object()

        if user != request_user and not request_user.is_superuser:
            raise PermissionDenied

        if not user.is_staff:
            raise Http404

        form = DateRangeForm(request.query_params)

        end_date = timezone.now()
        start_date = end_date - datetime.timedelta(days=7)

        if form.is_valid():
            form_dates = form.cleaned_data['timestamp']
            if form_dates and form_dates.start and form_dates.stop:
                start_date = form_dates.start
                end_date = form_dates.stop
        else:
            return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)

        result = user.staff_actions(start_date, end_date)

        return Response(result)


class WebsiteViewSet(PermissionReadOnlyModelViewSet):
    queryset = Website.objects.all()
    serializer_class = WebsiteSerializer
    filter_backends = (rest_framework.DjangoFilterBackend, OrderingFilter)
    filter_class = WebsiteFilterSet


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


class CategoryViewSet(LoggingMixin, PermissionReadOnlyModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    def get_queryset(self):
        return create_category_filter()(self.request)

    @detail_route()
    def specs_filters(self, request, pk, *args, **kwargs):
        category = self.get_object()

        specs_filters = category.categoryspecsfilter_set.select_related(
            'meta_model')
        serializer = CategorySpecsFilterSerializer(specs_filters, many=True)

        return Response(serializer.data)

    @detail_route()
    def specs_orders(self, request, pk, *args, **kwargs):
        category = self.get_object()

        specs_orders = category.categoryspecsorder_set.all()
        serializer = CategorySpecsOrderSerializer(specs_orders, many=True)

        return Response(serializer.data)

    @detail_route()
    def products(self, request, pk, *args, **kwargs):
        category = self.get_object()
        form_class = category.specs_form()
        form = form_class(request.query_params)
        if form.is_valid():
            es_products_search = form.get_es_products()

            paginator = ProductPagination()
            page = request.query_params.get(paginator.page_query_param, 1)
            try:
                page = int(page)
            except ValueError:
                page = 1

            page_size = paginator.get_page_size(request)

            offset = (page - 1) * page_size
            upper_bound = page * page_size

            es_products_page = es_products_search[offset:upper_bound].execute()

            # Page contents

            product_ids = [es_product.product_id
                           for es_product in es_products_page]

            db_products = Product.objects.filter(
                pk__in=product_ids).select_related(
                'instance_model__model__category')
            db_products_dict = iterable_to_dict(db_products, 'id')

            products = []
            for es_product in es_products_page:
                db_product = db_products_dict[es_product.product_id]
                db_product._specs = es_product.to_dict()
                products.append(db_product)

            serializer = ProductSerializer(products, many=True,
                                           context={'request': request})

            # Overall aggregations

            aggs = form.process_es_aggs(es_products_page.aggs)

            return Response({
                'count': es_products_page.hits.total,
                'results': serializer.data,
                'aggs': aggs,
            })
        else:
            return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)

    @detail_route()
    def browse(self, request, pk, *args, **kwargs):
        category = self.get_object()
        form = ProductsBrowseForm(request.query_params)
        result = form.get_category_products(category, request)

        return Response(result)


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

    @detail_route()
    def navigation(self, request, pk, *args, **kwargs):
        country = self.get_object()
        nav_departments = NavDepartment.objects.filter(
            country=country).prefetch_related('sections__items')
        serializer = NavDepartmentSerializer(nav_departments, many=True)
        return Response(serializer.data)


class StoreViewSet(PermissionReadOnlyModelViewSet):
    queryset = Store.objects.all()
    serializer_class = StoreSerializer
    filter_backends = (rest_framework.DjangoFilterBackend, SearchFilter,
                       OrderingFilter)
    filter_class = StoreFilterSet

    @list_route()
    def average_ratings(self, request, *args, **kwargs):
        stores = self.filter_queryset(self.get_queryset())

        ratings = Rating.objects.filter(
            store__in=stores,
            approval_date__isnull=False
        ).values('store')\
            .annotate(rating=Avg('store_rating'))\
            .order_by('store')

        stores_dict = {s.id: s for s in stores}

        store_ratings = [{
            'store': stores_dict[rating['store']],
            'rating': rating['rating']
        } for rating in ratings]

        serializer = StoreRatingSerializer(store_ratings, many=True,
                                           context={'request': request})
        return Response(serializer.data)

    @detail_route()
    @detail_permission('update_store_pricing')
    def scraper(self, request, pk):
        store = self.get_object()
        try:
            store.scraper
        except AttributeError:
            raise Http404
        serializer = StoreScraperSerializer(
            store,
            context={'request': request})
        available_categories = create_category_filter(
            qs=store.scraper_categories())(request)

        result = serializer.data
        result['categories'] = [
            reverse('category-detail', kwargs={'pk': category.pk},
                    request=request)
            for category in available_categories]

        return Response(result)

    @detail_route(methods=['post'])
    @detail_permission('update_store_pricing')
    def update_pricing(self, request, pk):
        store = self.get_object()
        form = StoreUpdatePricingForm.from_store_and_user(
            store, request.user, request.data)

        if form.is_valid():
            cleaned_data = form.cleaned_data

            categories = cleaned_data['categories']
            if categories:
                # The request specifies the categories to update
                category_ids = [category.id for category in categories]
            elif form.default_categories().count() == \
                    store.scraper_categories().count():
                # The request does not specify the categories, and the user
                # has permissions over all of the categories available to the
                # scraper. Setting category_ids to None tells the updating
                # process to also update the store entities whose type is not
                # in the scraper official list (e.g. "power supplies" in Paris
                # gaming section).
                category_ids = None
            else:
                # The request does not specify the categories, and the user
                # only has permission over a subset of the available categories
                # Use the categories with permissions.
                category_ids = [category.id
                                for category in form.default_categories()]

            discover_urls_concurrency = \
                cleaned_data['discover_urls_concurrency']
            products_for_url_concurrency = \
                cleaned_data['products_for_url_concurrency']
            use_async = cleaned_data['async']

            store_update_log = StoreUpdateLog.objects.create(store=store)

            task = store_update.delay(
                store.id,
                category_ids=category_ids,
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
            return Response(form.errors)


class StoreUpdateLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = StoreUpdateLog.objects.all()
    serializer_class = StoreUpdateLogSerializer
    pagination_class = StoreUpdateLogPagination
    filter_backends = (rest_framework.DjangoFilterBackend, OrderingFilter)
    filter_class = StoreUpdateLogFilterSet
    ordering_fields = ('last_updated', )

    @list_route()
    def latest(self, request, *args, **kwargs):
        stores = create_store_filter('view_store_update_logs')(self.request)

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


class EntityViewSet(LoggingMixin, viewsets.ReadOnlyModelViewSet):
    queryset = Entity.objects.all()
    pagination_class = EntityPagination
    serializer_class = EntitySerializer
    filter_backends = (rest_framework.DjangoFilterBackend, SearchFilter,
                       CustomEntityOrderingFilter)
    filter_class = EntityFilterSet
    search_fields = ('product__instance_model__unicode_representation',
                     'cell_plan__instance_model__unicode_representation',
                     'name',
                     'cell_plan_name',
                     'part_number',
                     'sku',
                     'ean',
                     'key',
                     'url',
                     'discovery_url')

    @list_route()
    def estimated_sales(self, request):
        if not request.user.is_authenticated:
            return Response(status=status.HTTP_403_FORBIDDEN)

        filterset = EntityEstimatedSalesFilterSet(
            data=request.query_params, request=request)
        form = EntityEstimatedSalesForm(request.query_params)

        if form.is_valid():
            result = form.estimated_sales(
                filterset.qs,
                request
            )

            grouping = form.cleaned_data['grouping']

            if grouping in ['entity', 'product']:
                paginator = EntitySalesEstimatePagination()
                page = paginator.paginate_queryset(result, request)
                return paginator.get_paginated_response(page)

            return Response(result)
        else:
            return Response({'detail': form.errors},
                            status=status.HTTP_400_BAD_REQUEST)

    @list_route()
    def conflicts(self, request):
        filterset = EntityStaffFilterSet(
            queryset=self.get_queryset(),
            data=request.query_params,
            request=request)

        serializer = EntityConflictSerializer(
            filterset.qs.conflicts(), many=True, context={'request': request})

        return Response(serializer.data)

    @list_route()
    def pending(self, request):
        filterset = EntityStaffFilterSet(
            queryset=self.get_queryset(),
            data=request.query_params,
            request=request)

        qs = filterset.qs.get_pending().order_by('-pk')

        paginator = self.paginator
        page = paginator.paginate_queryset(qs, request)

        serializer = EntitySerializer(page, many=True,
                                      context={'request': request})

        return paginator.get_paginated_response(serializer.data)

    @list_route()
    def by_url(self, request):
        form = EntityByUrlForm(request.query_params)

        if not form.is_valid():
            return Response({'errors': form.errors},
                            status=status.HTTP_400_BAD_REQUEST)

        entity = form.get_entity()

        if not entity:
            return Response({'errors': 'No matching entity found'},
                            status=status.HTTP_404_NOT_FOUND)

        serializer = EntitySerializer(entity, context={'request': request})
        return Response(serializer.data)

    @detail_route(methods=['post'])
    def register_staff_access(self, request, *args, **kwargs):
        entity = self.get_object()
        if not entity.user_has_staff_perms(request.user):
            raise PermissionDenied

        entity.update_keeping_log(
            {
                'last_staff_access_user': request.user,
                'last_staff_access': timezone.now(),
            },
            request.user)

        serialized_data = EntitySerializer(
            entity, context={'request': self.request}).data
        return Response(serialized_data)

    @detail_route(methods=['post'])
    def update_pricing(self, request, *args, **kwargs):
        entity = self.get_object()
        user = request.user

        has_perm = user.has_perm('update_store_pricing', entity.store) \
            or entity.user_has_staff_perms(user) \
            or user.has_perm('update_category_entities_pricing',
                             entity.category)

        if not has_perm:
            raise PermissionDenied

        try:
            entity.update_pricing()
            serialized_data = EntitySerializer(
                entity, context={'request': self.request}).data
            return Response(serialized_data)
        except Exception as e:
            recipients = get_user_model().objects.filter(is_superuser=True)

            for recipient in recipients:
                recipient.send_entity_update_failure_email(
                    entity, request.user, traceback.format_exc())

            return Response({'detail': str(e)},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @detail_route()
    def events(self, request, *args, **kwargs):
        entity = self.get_object()
        serialized_events = []

        def serialize_value(value):
            if isinstance(value, models.Model):
                return EntityEventValueSerializer(value).data
            else:
                return value

        for event in entity.events():
            serialized_changes = []
            for change in event['changes']:
                serialized_changes.append({
                    'field': change['field'],
                    'old_value': serialize_value(change['old_value']),
                    'new_value': serialize_value(change['new_value'])
                })

            serialized_event = {
                'timestamp': event['timestamp'],
                'user': EntityEventUserSerializer(
                    event['user'], context={'request': request}).data,
                'changes': serialized_changes
            }

            serialized_events.append(serialized_event)

        return Response(serialized_events)

    @detail_route(methods=['post'])
    def toggle_visibility(self, request, *args, **kwargs):
        entity = self.get_object()
        if not entity.user_has_staff_perms(request.user):
            raise PermissionDenied

        try:
            entity.update_keeping_log(
                {
                    'is_visible': not entity.is_visible,
                },
                request.user)
            serialized_data = EntitySerializer(
                entity, context={'request': self.request}).data
            return Response(serialized_data)
        except IntegrityError as err:
            return Response({'detail': str(err)},
                            status=status.HTTP_400_BAD_REQUEST)

    @detail_route(methods=['post'])
    def change_category(self, request, *args, **kwargs):
        entity = self.get_object()
        if not entity.user_has_staff_perms(request.user):
            raise PermissionDenied

        if entity.product:
            return Response({'detail': 'Cannot change category of '
                                       'associated entities'},
                            status=status.HTTP_400_BAD_REQUEST)

        form = CategoryForm(request.data)

        if form.is_valid():
            new_category = form.cleaned_data['category']
            if new_category == entity.category:
                return Response({'detail': 'The new category must be '
                                           'different from the original one'},
                                status=status.HTTP_400_BAD_REQUEST)

            entity.update_keeping_log(
                {
                    'category': new_category,
                },
                request.user)
            serialized_data = EntitySerializer(
                entity, context={'request': self.request}).data
            return Response(serialized_data)
        else:
            return Response({'detail': form.errors},
                            status=status.HTTP_400_BAD_REQUEST)

    @detail_route(methods=['post', ])
    def associate(self, request, *args, **kwargs):
        entity = self.get_object()
        if not entity.user_has_staff_perms(request.user):
            raise PermissionDenied

        form = EntityAssociationForm(request.data)
        if not form.is_valid():
            return Response({
                'errors': form.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        product = form.cleaned_data['product']
        cell_plan = form.cleaned_data['cell_plan']

        try:
            entity.associate(request.user, product, cell_plan)
        except Exception as ex:
            return Response(
                {'detail': str(ex)},
                status=status.HTTP_400_BAD_REQUEST)

        if entity.cell_plan_name:
            entity.associate_related_cell_entities(request.user)

        serialized_data = EntitySerializer(
            entity, context={'request': self.request}).data
        return Response(serialized_data)

    @detail_route(methods=['post', ])
    def dissociate(self, request, *args, **kwargs):
        entity = self.get_object()
        if not entity.user_has_staff_perms(request.user):
            raise PermissionDenied

        form = EntityDisssociationForm(request.data)
        if not form.is_valid():
            return Response({
                'errors': form.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            entity.dissociate(request.user, form.cleaned_data['reason'])
        except Exception as ex:
            return Response(
                {'detail': str(ex)},
                status=status.HTTP_400_BAD_REQUEST)

        serialized_data = EntitySerializer(
            entity, context={'request': self.request}).data
        return Response(serialized_data)

    @detail_route()
    def pricing_history(self, request, pk):
        entity = self.get_object()

        if entity.user_can_view_stocks(request.user):
            serializer_klass = EntityHistoryWithStockSerializer
        else:
            serializer_klass = EntityHistorySerializer

        filterset = EntityHistoryFilterSet(
            data=request.query_params,
            queryset=entity.entityhistory_set.all(),
            request=request)
        serializer = serializer_klass(
            filterset.qs,
            many=True,
            context={'request': request}
        )
        return Response(serializer.data)

    @detail_route()
    def staff_info(self, request, pk):
        entity = self.get_object()
        if not entity.user_has_staff_perms(request.user):
            raise PermissionDenied
        serialializer = EntityStaffInfoSerializer(
            entity, context={'request': request})
        return Response(serialializer.data)

    @detail_route()
    def cell_plan_choices(self, request, *args, **kwargs):
        entity = self.get_object()
        if not entity.user_has_staff_perms(request.user):
            raise PermissionDenied

        cell_category = Category.objects.get(pk=settings.CELL_CATEGORY)
        cell_plan_category = Category.objects.get(
            pk=settings.CELL_PLAN_CATEGORY)

        if entity.category != cell_category:
            cell_plan_choices = Product.objects.none()
        elif entity.cell_plan_name:
            filter_parameters = {
                'association_name.keyword': entity.cell_plan_name
            }

            matching_cell_plans = cell_plan_category.es_search() \
                .filter('term', **filter_parameters) \
                .execute()

            cell_plan_ids = [x.product_id for x in matching_cell_plans]
            cell_plan_choices = Product.objects.filter(pk__in=cell_plan_ids)
        else:
            cell_plan_choices = Product.objects.filter_by_category(
                cell_plan_category).filter(
                instance_model__unicode_representation__icontains='prepago')

        serializer = NestedProductSerializer(cell_plan_choices, many=True,
                                             context={'request': request})
        return Response(serializer.data)

    @detail_route(methods=['post'])
    def register_lead(self, request, pk):
        entity = self.get_object()

        if not entity.active_registry:
            return Response(
                {'error': 'Then requested entity does not have an '
                          'associated registry, so it can\'t register leads'},
                status=status.HTTP_400_BAD_REQUEST)

        if request.user.is_authenticated:
            user = request.user
        else:
            user = get_anonymous_user()

        form = WebsiteForm.from_user(user, request.data)

        if form.is_valid():
            website = form.cleaned_data['website']
            ip = get_client_ip(request) or '127.0.0.1'

            lead = Lead.objects.create(
                entity_history=entity.active_registry,
                website=website,
                user=user,
                ip=ip
            )

            return Response(LeadSerializer(
                lead, context={'request': request}).data)
        else:
            return Response(form.errors)

    @detail_route()
    def affiliate_url(self, request, pk, *args, **kwargs):
        entity = self.get_object()

        affiliate_url = entity.affiliate_url()

        if not affiliate_url:
            raise Http404

        return Response({'affiliate_url': affiliate_url})


class EntityHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = EntityHistory.objects.all()
    serializer_class = EntityHistorySerializer
    pagination_class = EntityHistoryPagination
    filter_backends = (rest_framework.DjangoFilterBackend, )
    filter_class = EntityHistoryFilterSet

    @detail_route()
    def stock(self, request, pk):
        entity_history = self.get_object()
        if entity_history.entity.user_can_view_stocks(request.user):
            return Response({'stock': entity_history.stock})
        else:
            raise PermissionDenied


class ProductViewSet(LoggingMixin, viewsets.ReadOnlyModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filter_backends = (rest_framework.DjangoFilterBackend, SearchFilter,
                       CustomProductOrderingFilter)
    filter_class = ProductFilterSet
    ordering_fields = None
    pagination_class = ProductPagination

    def _should_log(self, request, response):
        for keyword in ['browse', 'entities']:
            if keyword in request.path:
                return True
        return False

    @list_route()
    def available_entities(self, request):
        cache_json = OrderedDict(dict(request.query_params))
        categories_with_permission = create_category_filter()(self.request)
        cache_json['category_permissions'] = \
            [s.id for s in categories_with_permission]
        stores_with_permission = create_store_filter()(self.request)
        cache_json['store_permissions'] = \
            [s.id for s in stores_with_permission]
        cache_json['method'] = 'product_available_entities'
        cache_key = generate_cache_key(cache_json)

        cached_result = cache.get(cache_key)

        if cached_result:
            result = json.loads(cached_result.decode('utf-8'))
            return Response(result)

        queryset = self.filter_queryset(self.get_queryset())
        products = self.paginate_queryset(queryset)
        Product.prefetch_specs(products)

        entities = Entity.objects \
            .filter(product__in=products) \
            .get_available() \
            .order_by('active_registry__offer_price')

        entity_query_params = request.query_params.copy()
        entity_query_params.pop('ids', None)
        entity_filterset = EntityFilterSet(data=entity_query_params,
                                           queryset=entities,
                                           request=request)

        result_dict = {}

        for product in products:
            result_dict[product] = []

        for entity in entity_filterset.qs:
            result_dict[entity.product].append(entity)

        result_array = [{'product': product, 'entities': entities}
                        for product, entities in result_dict.items()]

        serializer = ProductAvailableEntitiesSerializer(
            result_array, many=True, context={'request': request})

        result = OrderedDict([
            ('count', self.paginator.page.paginator.count),
            ('next', self.paginator.get_next_link()),
            ('previous', self.paginator.get_previous_link()),
            ('results', serializer.data)
        ])

        serialized_result = JSONRenderer().render(result)
        cache.set(cache_key, serialized_result)

        return Response(result)

    @list_route()
    def browse(self, request, *args, **kwargs):
        form = ProductsBrowseForm(request.query_params)
        result = form.get_products(request)
        return Response(result)

    @detail_route()
    def entities(self, request, pk):
        product = self.get_object()
        stores = Store.objects.filter_by_user_perms(request.user, 'view_store')
        product_entities = product.entity_set.filter(store__in=stores)
        serializer = EntitySerializer(product_entities, many=True,
                                      context={'request': request})
        return Response(serializer.data)

    @detail_route(methods=['post', ])
    def clone(self, request, pk):
        product = self.get_object()
        if not product.user_has_staff_perms(request.user):
            raise PermissionDenied

        cloned_instance = product.instance_model.clone(request.user.id)

        return Response({
            'instance_id': cloned_instance.id
        })

    @detail_route()
    def pricing_history(self, request, pk):
        product = self.get_object()
        entity_histories = EntityHistory.objects.filter(
            entity__product=product,
            cell_monthly_payment__isnull=True,
        )

        filterset = EntityHistoryFilterSet(request.query_params,
                                           entity_histories)
        entity_histories = filterset.qs \
            .order_by('entity', 'timestamp') \
            .select_related('entity__product__instance_model',
                            'entity__cell_plan__instance_model')

        histories_by_entity = OrderedDict()
        for entity_history in entity_histories:
            if entity_history.entity not in histories_by_entity:
                histories_by_entity[entity_history.entity] = [entity_history]
            else:
                histories_by_entity[entity_history.entity].append(
                    entity_history)

        result_for_serialization = [
            {'entity': entity, 'pricing_history': pricing_history}
            for entity, pricing_history in histories_by_entity.items()]

        serializer = ProductPricingHistorySerializer(
            result_for_serialization, many=True, context={'request': request})

        return Response(serializer.data)

    @detail_route(methods=['post'])
    def register_visit(self, request, pk):
        product = self.get_object()

        if request.user.is_authenticated:
            user = request.user
        else:
            user = get_anonymous_user()

        form = WebsiteForm.from_user(user, request.data)

        if form.is_valid():
            website = form.cleaned_data['website']
            ip = get_client_ip(request) or '127.0.0.1'

            visit = Visit.objects.create(
                product=product,
                website=website,
                user=user,
                ip=ip
            )

            return Response(VisitSerializer(
                visit, context={'request': request}).data)
        else:
            return Response(form.errors)

    @detail_route()
    def bucket(self, request, pk):
        product = self.get_object()

        form = ProductBucketFieldForm(request.query_params)

        if not form.is_valid():
            return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)

        fields = form.cleaned_data['fields'].split(',')
        product_specs = product.specs
        search = product.category.es_search()

        for field in fields:
            field_value = product_specs.get(field)
            search = search.filter('term', **{field: field_value})

        es_products_dict = {
            es_product.product_id: es_product.to_dict()
            for es_product in search[:100].execute()
        }

        bucket_products = Product.objects.filter(
            pk__in=es_products_dict.keys()
        ).select_related('instance_model__model__category')

        for product in bucket_products:
            product._specs = es_products_dict[product.id]

        serializer = ProductSerializer(
            bucket_products, many=True, context={'request': request})
        return Response(serializer.data)

    @detail_route()
    def render(self, request, pk):
        from category_templates.models import CategoryTemplate
        from category_templates.forms import ProductRenderForm

        product = self.get_object()

        form = ProductRenderForm.from_user(request.user, request.query_params)

        if not form.is_valid():
            return Response(form.errors)

        category_template = get_object_or_404(
            CategoryTemplate,
            category=product.category,
            website=form.cleaned_data['website'],
            purpose=form.cleaned_data['purpose'],
        )

        try:
            # While we are migrating to Handlebars templates
            rendered_template = category_template.render(product)
            return Response({
                'result': rendered_template
            })
        except Exception:
            return Response(status=status.HTTP_400_BAD_REQUEST)

    @detail_route()
    def picture(self, request, pk):
        product = self.get_object()

        form = ProductPictureForm(request.query_params)

        if not form.is_valid():
            return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)

        specs = product.specs

        if 'picture' not in specs:
            raise Response({'detail': 'No picture found for product'},
                           status=status.HTTP_404_NOT_FOUND)

        picture = specs['picture']
        dimensions = '{}x{}'.format(form.cleaned_data['width'],
                                    form.cleaned_data['height'])
        resized_picture = get_thumbnail(picture, dimensions)

        response = Response(status=status.HTTP_302_FOUND)
        response['Location'] = resized_picture.url
        return response

    @detail_route()
    def average_rating(self, request, pk):
        product = self.get_object()

        rating = product.rating_set.filter(approval_date__isnull=False)\
            .aggregate(average=Avg('product_rating'), count=Count('*'))

        return Response(rating)


class LeadViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Lead.objects.all()
    serializer_class = LeadSerializer
    filter_backends = (rest_framework.DjangoFilterBackend, SearchFilter,
                       OrderingFilter)
    filter_class = LeadFilterSet
    pagination_class = LeadPagination
    ordering_fields = ('timestamp',)

    def get_serializer_class(self):
        if self.request.user.has_perm('solotodo.view_leads_user_data'):
            return LeadWithUserDataSerializer
        else:
            return LeadSerializer

    @list_route()
    def grouped(self, request):
        filterset = LeadFilterSet(
            data=request.query_params,
            request=request)

        form = LeadGroupingForm(request.query_params)

        if form.is_valid():
            result = form.aggregate(request, filterset.qs)

            groupings = form.cleaned_data['grouping']

            if 'entity' in groupings or 'product' in groupings:
                paginator = LeadPagination()
                page = paginator.paginate_queryset(result, request)
                return paginator.get_paginated_response(page)

            return Response(result)
        else:
            return Response({'detail': form.errors},
                            status=status.HTTP_400_BAD_REQUEST)


class VisitViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Visit.objects.all()
    serializer_class = VisitSerializer
    filter_backends = (rest_framework.DjangoFilterBackend, OrderingFilter)
    filter_class = VisitFilterSet
    pagination_class = VisitPagination
    ordering_fields = ('timestamp',)

    def get_serializer_class(self):
        if self.request.user.has_perm('solotodo.view_visits_user_data'):
            return VisitWithUserDataSerializer
        else:
            return VisitSerializer

    @list_route()
    def grouped(self, request):
        filterset = VisitFilterSet(
            data=request.query_params,
            request=request)

        form = VisitGroupingForm(request.query_params)

        if form.is_valid():
            result = form.aggregate(request, filterset.qs)

            groupings = form.cleaned_data['grouping']

            if 'product' in groupings:
                paginator = VisitPagination()
                page = paginator.paginate_queryset(result, request)
                return paginator.get_paginated_response(page)

            return Response(result)
        else:
            return Response({'detail': form.errors},
                            status=status.HTTP_400_BAD_REQUEST)


class ResourceViewSet(viewsets.ViewSet):
    def list(self, request):
        form = ResourceNamesForm(request.query_params)

        if not form.is_valid():
            return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)

        resource_names = form.cleaned_data['names']
        if not resource_names:
            resource_names = [choice[0] for choice in
                              ResourceNamesForm.choices]

        response = []

        for resource_name in resource_names:
            resource_model_and_serializer = \
                ResourceNamesForm.model_map[resource_name]
            model = resource_model_and_serializer['model']
            serializer = resource_model_and_serializer['serializer']

            if resource_model_and_serializer['permission']:
                model_objects = get_objects_for_user(
                    request.user, resource_model_and_serializer['permission'],
                    klass=model)
            else:
                model_objects = model.objects.all()

            resource_entries = serializer(model_objects, many=True,
                                          context={'request': request})
            response.extend(resource_entries.data)

        return Response(response)


class RatingViewSet(viewsets.ModelViewSet):
    queryset = Rating.objects.all()
    serializer_class = RatingSerializer
    permission_classes = (RatingPermission, )
    pagination_class = RatingPagination
    filter_backends = (rest_framework.DjangoFilterBackend, OrderingFilter)
    filter_class = RatingFilterSet

    def get_serializer_class(self):
        if self.action == 'create':
            return RatingCreateSerializer

        if self.request.user.has_perm('solotodo.is_ratings_staff'):
            return RatingFullSerializer

        return RatingSerializer

    @detail_route(methods=['post'])
    def approve(self, request, pk, *args, **kwargs):
        if not request.user.has_perm('solotodo.is_ratings_staff'):
            return Response(status=status.HTTP_403_FORBIDDEN)

        rating = self.get_object()

        try:
            rating.approve()
        except ValidationError as err:
            return Response({'detail': err},
                            status=status.HTTP_400_BAD_REQUEST)

        serializer_class = self.get_serializer_class()
        serializer = serializer_class(rating, context={'request': request})
        return Response(serializer.data)
