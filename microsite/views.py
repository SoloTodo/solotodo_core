from rest_framework import viewsets, mixins

from .models import MicrositeBrand
from .serializers import MicrositeBrandSerializer


class MicrositeBrandViewSet(mixins.RetrieveModelMixin,
                            mixins.ListModelMixin,
                            viewsets.GenericViewSet):
    queryset = MicrositeBrand.objects.all()
    serializer_class = MicrositeBrandSerializer
