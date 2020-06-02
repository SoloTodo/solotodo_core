from rest_framework import viewsets, mixins

from .models import MicrositeBrand, MicrositeEntry
from .serializers import MicrositeBrandSerializer, MicrositeEntrySerializer


class MicrositeBrandViewSet(mixins.RetrieveModelMixin,
                            mixins.ListModelMixin,
                            viewsets.GenericViewSet):
    queryset = MicrositeBrand.objects.all()
    serializer_class = MicrositeBrandSerializer

    def get_queryset(self):
        user = self.request.user
        return MicrositeBrand.objects.filter_by_user_perms(
            user, 'change_microsite_brand')


class MicrositeEntryViewset(mixins.RetrieveModelMixin,
                            mixins.ListModelMixin,
                            viewsets.GenericViewSet):
    queryset = MicrositeEntry.objects.all()
    serializer_class = MicrositeEntrySerializer

    def get_queryset(self):
        user = self.request.user
        return MicrositeEntry.objects.filter_by_user_perms(
            user, 'change_microsite_brand')
