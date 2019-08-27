from rest_framework import viewsets, mixins, status

from .models import StoreSubscription
from .serializers import StoreSubscriptionSerializer


class StoreSubscriptionViewSet(mixins.CreateModelMixin,
                               mixins.RetrieveModelMixin,
                               mixins.ListModelMixin,
                               viewsets.GenericViewSet):
    queryset = StoreSubscription.objects.all()
    serializer_class = StoreSubscriptionSerializer

    def get_queryset(self):
        user = self.request.user

        if not user.is_authenticated:
            return StoreSubscription.objects.none()
        elif user.is_superuser:
            return StoreSubscription.objects.all()
        else:
            return StoreSubscription.objects.filter(user=user)
