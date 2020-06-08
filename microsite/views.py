from rest_framework import viewsets, mixins, status
from rest_framework.decorators import detail_route
from rest_framework.response import Response

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
            user, 'view_microsite_brand')

    @detail_route(methods=['post'])
    def add_entry(self, request, pk, *args, **kwargs):
        user = self.request.user
        microsite_brand = self.get_object()
        product_id = request.data.get('product_id')

        if not user.has_perm('change_microsite_brand', microsite_brand):
            return Response({
                'errors': 'User has no permission to change this brand'
            }, status=status.HTTP_401_UNAUTHORIZED)

        if not product_id:
            return Response({
                'errors': 'No id'
            }, status=status.HTTP_400_BAD_REQUEST)

        microsite_brand.create_entry_from_product(product_id)

        serializer = MicrositeBrandSerializer(
            microsite_brand, context={'request': request})

        return Response(serializer.data)


class MicrositeEntryViewset(mixins.RetrieveModelMixin,
                            mixins.ListModelMixin,
                            mixins.UpdateModelMixin,
                            mixins.DestroyModelMixin,
                            viewsets.GenericViewSet):
    queryset = MicrositeEntry.objects.all()
    serializer_class = MicrositeEntrySerializer

    def get_queryset(self):
        user = self.request.user
        return MicrositeEntry.objects.filter_by_user_perms(
            user, 'change_microsite_brand')
