from rest_framework import viewsets, mixins, status
from rest_framework.decorators import list_route, detail_route
from rest_framework.response import Response
from django_filters import rest_framework
from django.db.models import Q
from rest_framework.filters import OrderingFilter, \
    SearchFilter

from alerts.forms import AlertDeleteByKeyForm
from .models import AnonymousAlert, UserAlert, ProductPriceAlert
from alerts.pagination import ProductPriceAlertPagination
from alerts.serializers import AnonymousAlertSerializer, \
    AnonymousAlertCreationSerializer, UserAlertSerializer, \
    UserAlertCreationSerializer, AlertNotificationSerializer, \
    ProductPriceAlertSerializer, ProductPriceAlertCreationSerializer


class AnonymousAlertViewSet(mixins.CreateModelMixin,
                            mixins.RetrieveModelMixin,
                            mixins.ListModelMixin,
                            viewsets.GenericViewSet):
    queryset = AnonymousAlert.objects.all()
    serializer_class = AnonymousAlertSerializer

    def get_queryset(self):
        user = self.request.user

        if not user.is_authenticated:
            return AnonymousAlert.objects.none()
        elif user.is_superuser:
            return AnonymousAlert.objects.all()
        else:
            return AnonymousAlert.objects.filter(email=user.email)

    def get_serializer_class(self):
        if self.action == 'create':
            return AnonymousAlertCreationSerializer
        else:
            return AnonymousAlertSerializer

    @list_route(methods=['post'])
    def delete_by_key(self, request, *args, **kwargs):
        form = AlertDeleteByKeyForm(request.data)
        if not form.is_valid():
            return Response({
                'errors': form.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        payload = form.cleaned_data['payload']
        alert_id = payload.get('anonymous_alert_id')

        if alert_id is None:
            return Response({
                'errors': ['Alert ID not found in payload']
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            alert = AnonymousAlert.objects.get(pk=alert_id)
        except AnonymousAlert.DoesNotExist:
            return Response({
                'errors': ['Matching alert not found']
            }, status=status.HTTP_404_NOT_FOUND)

        alert.delete()
        return Response({'status': 'deleted'})


class UserAlertViewSet(mixins.CreateModelMixin,
                       mixins.RetrieveModelMixin,
                       mixins.ListModelMixin,
                       mixins.DestroyModelMixin,
                       viewsets.GenericViewSet):

    queryset = UserAlert.objects.all()
    serializer_class = UserAlertSerializer
    filter_backends = (rest_framework.DjangoFilterBackend, SearchFilter,
                       OrderingFilter)
    ordering_fields = ('id', 'alert__creation_date')

    def get_queryset(self):
        user = self.request.user

        if not user.is_authenticated:
            return UserAlert.objects.none()
        elif user.is_superuser:
            return UserAlert.objects.all()
        else:
            return UserAlert.objects.filter(user=user)

    def get_serializer_class(self):
        if self.action == 'create':
            return UserAlertCreationSerializer
        else:
            return UserAlertSerializer

    @detail_route()
    def alert_notifications(self, request, pk, *args, **kwargs):
        user_alert = self.get_object()

        alert_notifications = user_alert.alert.notifications \
            .order_by('creation_date') \
            .select_related(
                'previous_normal_price_registry'
                '__entity__product__instance_model',
                'previous_offer_price_registry'
                '__entity__product__instance_model',
                'previous_normal_price_registry__entity__active_registry',
                'previous_offer_price_registry__entity__active_registry')
        serializer = AlertNotificationSerializer(
            alert_notifications, many=True, context={'request': request})

        return Response(serializer.data)


class ProductPriceAlertViewSet(mixins.CreateModelMixin,
                               mixins.RetrieveModelMixin,
                               mixins.ListModelMixin,
                               mixins.DestroyModelMixin,
                               viewsets.GenericViewSet):

    queryset = ProductPriceAlert.objects.all()
    serializer_class = ProductPriceAlertSerializer
    pagination_class = ProductPriceAlertPagination
    filter_backends = (rest_framework.DjangoFilterBackend, SearchFilter,
                       OrderingFilter)
    ordering_fields = ('id', 'creation_date')

    def get_queryset(self):
        user = self.request.user

        if not user.is_authenticated:
            return ProductPriceAlert.objects.none()
        elif user.is_superuser:
            return ProductPriceAlert.objects.all()
        else:
            return ProductPriceAlert.objects.filter(
                Q(email=user.email) | Q(user=user))

    def get_serializer_class(self):
        if self.action == 'create':
            return ProductPriceAlertCreationSerializer
        else:
            return ProductPriceAlertSerializer
