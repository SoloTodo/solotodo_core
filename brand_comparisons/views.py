from .models import BrandComparison, BrandComparisonSegment, \
    BrandComparisonSegmentRow
from .serializers import BrandComparisonSerializer, \
    FullBrandComparisonSerializer, BrandComparisonSegmentSerializer, \
    BrandComparisonSegmentRowSerializer

from rest_framework import viewsets, mixins


class BrandComparisonViewSet(mixins.RetrieveModelMixin,
                             mixins.ListModelMixin,
                             viewsets.GenericViewSet):
    queryset = BrandComparison.objects.all()
    serializer_class = FullBrandComparisonSerializer

    def get_queryset(self):
        user = self.request.user

        if not user.is_authenticated:
            return BrandComparison.objects.none()
        elif user.is_superuser:
            return BrandComparison.objects.all()
        else:
            return BrandComparison.objects.filter(user=user)

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return FullBrandComparisonSerializer
        else:
            return BrandComparisonSerializer


class BrandComparisonSegmentViewSet(mixins.RetrieveModelMixin,
                                    mixins.ListModelMixin,
                                    viewsets.GenericViewSet):
    queryset = BrandComparisonSegment.objects.all()
    serializer_class = BrandComparisonSegmentSerializer


class BrandComparisonSegmentRowViewSet(mixins.RetrieveModelMixin,
                                       mixins.ListModelMixin,
                                       viewsets.GenericViewSet):
    queryset = BrandComparisonSegmentRow.objects.all()
    serializer_class = BrandComparisonSegmentRowSerializer
