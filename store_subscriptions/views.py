from rest_framework import viewsets, mixins

from .models import StoreSubscription
from .serializers import StoreSubscriptionSerializer, \
    StoreSubscriptionCreationSerializer
from .pagination import StoreSubscriptionPagination


class StoreSubscriptionViewSet(mixins.CreateModelMixin,
                               mixins.RetrieveModelMixin,
                               mixins.ListModelMixin,
                               mixins.DestroyModelMixin,
                               viewsets.GenericViewSet):
    queryset = StoreSubscription.objects.all()
    serializer_class = StoreSubscriptionSerializer
    pagination_class = StoreSubscriptionPagination

    def get_queryset(self):
        user = self.request.user

        if not user.is_authenticated:
            return StoreSubscription.objects.none()
        elif user.is_superuser:
            return StoreSubscription.objects.all()
        else:
            return StoreSubscription.objects.filter(user=user)

    def get_serializer_class(self):
        if self.action == 'create':
            return StoreSubscriptionCreationSerializer
        else:
            return StoreSubscriptionSerializer
