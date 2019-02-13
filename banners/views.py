from rest_framework import viewsets, mixins, status

from .models import Banner
from .serializers import BannerSerializer


class BannerViewSet(mixins.CreateModelMixin,
                    mixins.RetrieveModelMixin,
                    mixins.ListModelMixin,
                    viewsets.GenericViewSet):
    queryset = Banner.objects.all()
    serializer_class = BannerSerializer

    def get_queryset(self):
        return self.queryset

    def get_serializer_class(self):
        return self.serializer_class
