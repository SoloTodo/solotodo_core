from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters import rest_framework
from django.db.models import Q
from rest_framework.filters import OrderingFilter, \
    SearchFilter

from alerts.forms import AlertDeleteByKeyForm
from .models import ProductPriceAlert
from alerts.pagination import ProductPriceAlertPagination
from alerts.serializers import ProductPriceAlertSerializer, \
    ProductPriceAlertCreationSerializer


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

    @action(methods=['post'], detail=False)
    def delete_by_key(self, request, *args, **kwargs):
        form = AlertDeleteByKeyForm(request.data)
        if not form.is_valid():
            return Response({
                'errors': form.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        payload = form.cleaned_data['payload']
        alert_id = payload.get('alert_id')

        if alert_id is None:
            return Response({
                'errors': ['Alert ID not found in payload']
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            alert = ProductPriceAlert.objects.get(pk=alert_id)
        except ProductPriceAlert.DoesNotExist:
            return Response({
                'errors': ['Matching alert not found']
            }, status=status.HTTP_404_NOT_FOUND)

        if alert.user:
            return Response({
                'errors': ['Matching alert not found']
            }, status=status.HTTP_404_NOT_FOUND)

        alert.delete()
        return Response({'status': 'deleted'})
