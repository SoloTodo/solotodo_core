from rest_framework import viewsets, mixins, status
from rest_framework.decorators import detail_route
from rest_framework.response import Response

from solotodo_core.s3utils import PrivateS3Boto3Storage
from .models import BrandComparison, BrandComparisonSegment, \
    BrandComparisonSegmentRow, BrandComparisonAlert
from .serializers import BrandComparisonSerializer, \
    FullBrandComparisonSerializer, BrandComparisonCreationSerializer,\
    BrandComparisonSegmentSerializer, BrandComparisonSegmentRowSerializer,\
    BrandComparisonUpdateSerializer, BrandComparisonSegmentRowUpdateSerializer\
    , BrandComparisonAlertSerializer
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
        qs = BrandComparison.objects.prefetch_related(
            'segments__rows__product_1__instance_model',
            'segments__rows__product_2__instance_model',
            'stores'
        ).select_related('user', 'brand_1', 'brand_2', 'category')

        group = user.groups.get()

        if not user.is_authenticated:
            return qs.none()
        elif user.is_superuser:
            return qs.all()
        else:
            return qs.filter(user__groups=group)

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return FullBrandComparisonSerializer
        elif self.action == 'create':
            return BrandComparisonCreationSerializer
        elif self.action == 'partial_update':
            return BrandComparisonUpdateSerializer
        else:
            return BrandComparisonSerializer

    def retrieve(self, request, *args, **kwargs):
        export_format = request.GET.get('export_format')

        if export_format == 'xls':
            brand_comparison = self.get_object()
            report_path = brand_comparison.as_xls()['path']
            storage = PrivateS3Boto3Storage()
            report_url = storage.url(report_path)
            return Response({
                'url': report_url
            })

        return super().retrieve(self, request, *args, **kwargs)

    @detail_route(methods=['post'])
    def add_segment(self, request, pk, *args, **kwargs):
        brand_comparison = self.get_object()
        segment_name = request.data.get('name')

        if not segment_name:
            return Response({
                'errors': 'No name'
            }, status=status.HTTP_400_BAD_REQUEST)

        brand_comparison.add_segment(segment_name)

        serializer = FullBrandComparisonSerializer(
            brand_comparison, context={'request': request})

        return Response(serializer.data)

    @detail_route(methods=['post'])
    def add_manual_product(self, request, pk, *args, **kwargs):
        brand_comparison = self.get_object()
        product_id = request.data.get('product_id')

        if not product_id:
            return Response({
                'errors': 'No id'
            }, status=status.HTTP_400_BAD_REQUEST)

        brand_comparison.add_manual_product(product_id)

        serializer = FullBrandComparisonSerializer(
            brand_comparison, context={'request': request})

        return Response(serializer.data)

    @detail_route(methods=['post'])
    def remove_manual_product(self, request, pk, *args, **kwargs):
        brand_comparison = self.get_object()
        product_id = request.data.get('product_id')

        if not product_id:
            return Response({
                'errors': 'No id'
            }, status=status.HTTP_400_BAD_REQUEST)

        brand_comparison.remove_manual_product(product_id)

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
        ordering = request.data.get('ordering')
        segment.add_row(ordering)

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

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if len(instance.segment.rows.all()) > 1:
            self.perform_destroy(instance)
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            return Response({
                'errors': 'Cant delete last row of segment.'
            }, status=status.HTTP_400_BAD_REQUEST)

    @detail_route(methods=['post'])
    def move(self, request, pk, *args, **kwargs):
        row = self.get_object()
        direction = request.data.get('direction')

        row.move(direction)

        serializer = BrandComparisonSegmentRowSerializer(
            row, context={'request': request})

        return Response(serializer.data)


class BrandComparisonAlertViewSet(mixins.RetrieveModelMixin,
                                  mixins.CreateModelMixin,
                                  mixins.ListModelMixin,
                                  mixins.DestroyModelMixin,
                                  viewsets.GenericViewSet):
    queryset = BrandComparisonAlert.objects.all()
    serializer_class = BrandComparisonAlertSerializer
