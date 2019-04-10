from rest_framework import viewsets, mixins, status
from rest_framework.decorators import detail_route
from rest_framework.response import Response

from .models import BrandComparison, BrandComparisonSegment, \
    BrandComparisonSegmentRow
from .serializers import BrandComparisonSerializer, \
    FullBrandComparisonSerializer, BrandComparisonCreationSerializer,\
    BrandComparisonSegmentSerializer, BrandComparisonSegmentRowSerializer,\
    BrandComparisonUpdateSerializer, BrandComparisonSegmentRowUpdateSerializer
from .pagination import BrandComparisonPagination


class BrandComparisonViewSet(mixins.CreateModelMixin,
                             mixins.RetrieveModelMixin,
                             mixins.ListModelMixin,
                             mixins.UpdateModelMixin,
                             mixins.DestroyModelMixin,
                             viewsets.GenericViewSet):
    queryset = BrandComparison.objects.all()
    serializer_class = FullBrandComparisonSerializer
    pagination_class = BrandComparisonPagination

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
        elif self.action == 'create':
            return BrandComparisonCreationSerializer
        elif self.action == 'partial_update':
            return BrandComparisonUpdateSerializer
        else:
            return BrandComparisonSerializer

    @detail_route(methods=['post'])
    def add_segment(self, request, pk, *args, **kwargs):
        brand_comparison = self.get_object()

        segment_name = request.data.get('name')

        if not segment_name:
            return Response({
                'errors': 'No name'
            }, status=status.HTTP_400_BAD_REQUEST)

        last_segment = brand_comparison.segments.last()

        if last_segment:
            next_ordering = last_segment.ordering + 1
        else:
            next_ordering = 1

        segment = BrandComparisonSegment.objects.create(
            name=segment_name,
            ordering=next_ordering,
            comparison=brand_comparison)

        BrandComparisonSegmentRow.objects.create(
            ordering=1,
            segment=segment)

        serializer = FullBrandComparisonSerializer(
            brand_comparison, context={'request': request})

        return Response(serializer.data)


class BrandComparisonSegmentViewSet(mixins.RetrieveModelMixin,
                                    mixins.ListModelMixin,
                                    mixins.UpdateModelMixin,
                                    mixins.DestroyModelMixin,
                                    viewsets.GenericViewSet):
    queryset = BrandComparisonSegment.objects.all()
    serializer_class = BrandComparisonSegmentSerializer

    def get_queryset(self):
        user = self.request.user

        if not user.is_authenticated:
            return BrandComparisonSegment.objects.none()
        elif user.is_superuser:
            return BrandComparisonSegment.objects.all()
        else:
            return BrandComparisonSegment.objects.filter(comparison__user=user)

    @detail_route(methods=['post'])
    def move(self, request, pk, *args, **kwargs):
        segment = self.get_object()
        direction = request.data.get('direction')

        segment.move(direction)

        serializer = BrandComparisonSegmentSerializer(
            segment, context={'request': request})

        return Response(serializer.data)

    @detail_route(methods=['post'])
    def add_row(self, request, pk, *args, ** kwargs):
        segment = self.get_object()

        next_ordering = segment.rows.last().ordering + 1

        BrandComparisonSegmentRow.objects.create(
            ordering=next_ordering,
            segment=segment)

        serializer = BrandComparisonSegmentSerializer(
            segment, context={'request': request})

        return Response(serializer.data)


class BrandComparisonSegmentRowViewSet(mixins.RetrieveModelMixin,
                                       mixins.ListModelMixin,
                                       mixins.UpdateModelMixin,
                                       mixins.DestroyModelMixin,
                                       viewsets.GenericViewSet):
    queryset = BrandComparisonSegmentRow.objects.all()
    serializer_class = BrandComparisonSegmentRowSerializer

    def get_serializer_class(self):
        if self.action == 'partial_update':
            return BrandComparisonSegmentRowUpdateSerializer
        else:
            return BrandComparisonSegmentRowSerializer

    @detail_route(methods=['post'])
    def move(self, request, pk, *args, **kwargs):
        row = self.get_object()
        direction = request.data.get('direction')

        row.move(direction)

        serializer = BrandComparisonSegmentRowSerializer(
            row, context={'request': request})

        return Response(serializer.data)
