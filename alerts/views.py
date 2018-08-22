from rest_framework import viewsets

from alerts.models import Alert
from alerts.serializers import AlertSerializer


class AlertViewSet(viewsets.ModelViewSet):
    queryset = Alert.objects.all()
    serializer_class = AlertSerializer

    def get_queryset(self):
        user = self.request.user

        if not user.is_authenticated:
            return Alert.objects.none()
        if user.is_superuser:
            return Alert.objects.all()
        else:
            return Alert.objects.filter(email=user.email)
