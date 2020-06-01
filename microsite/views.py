from rest_framework import viewsets, mixins

from .models import MicrositeBrand, MicrositeEntry
from .serializers import MicrositeBrandSerializer, MicrositeEntrySerializer


class MicrositeBrandViewSet(mixins.RetrieveModelMixin,
                            mixins.ListModelMixin,
                            viewsets.GenericViewSet):
    queryset = MicrositeBrand.objects.all()
    serializer_class = MicrositeBrandSerializer


class MicrositeEntryViewset(mixins.RetrieveModelMixin,
                            mixins.ListModelMixin,
                            viewsets.GenericViewSet):
    queryset = MicrositeEntry.objects.all()
    serializer_class = MicrositeEntrySerializer
