from rest_framework import viewsets, mixins, status
from rest_framework.decorators import list_route
from rest_framework.response import Response

from alerts.forms import AlertDeleteByKeyForm
from alerts.models import Alert
from alerts.serializers import AlertSerializer, AlertCreationSerializer


class AlertViewSet(mixins.CreateModelMixin,
                   mixins.RetrieveModelMixin,
                   mixins.ListModelMixin,
                   viewsets.GenericViewSet):
    queryset = Alert.objects.all()
    serializer_class = AlertSerializer

    def get_queryset(self):
        user = self.request.user

        if not user.is_authenticated:
            return Alert.objects.none()
        elif user.is_superuser:
            return Alert.objects.all()
        else:
            return Alert.objects.filter(email=user.email)

    def get_serializer_class(self):
        if self.action == 'create':
            return AlertCreationSerializer
        else:
            return AlertSerializer

    @list_route(methods=['post'])
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
            alert = Alert.objects.get(pk=alert_id)
        except Alert.DoesNotExist:
            return Response({
                'errors': ['Matching alert not found']
            }, status=status.HTTP_404_NOT_FOUND)

        alert.delete()
        return Response({'status': 'deleted'})
