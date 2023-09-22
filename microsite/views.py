from collections import OrderedDict

from django.db.models import Q
from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import MicrositeBrand, MicrositeEntry
from solotodo.models import Product, Entity
from .serializers import MicrositeBrandSerializer, MicrositeEntrySerializer, \
    MicrositeEntrySiteSerializer


class MicrositeBrandViewSet(mixins.RetrieveModelMixin,
                            mixins.ListModelMixin,
                            viewsets.GenericViewSet):
    queryset = MicrositeBrand.objects.all()
    serializer_class = MicrositeBrandSerializer

    def get_queryset(self):
        user = self.request.user
        return MicrositeBrand.objects.filter_by_user_perms(
            user, 'view_microsite_brand')

    @action(methods=['post'], detail=True)
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

    @action(methods=['get'], detail=True)
    def site_data(self, request, pk, *args, **kwargs):
        from wtb.models import WtbEntity, WtbBrand
        from wtb.forms import WtbBrandForm

        microsite_brand = self.get_object()
        form = WtbBrandForm(request.query_params)

        if not form.is_valid():
            return Response(form.errors, status=400)

        wtb_brand = form.cleaned_data['wtb_brand']
        if not wtb_brand:
            # LG CL is the default
            wtb_brand = WtbBrand.objects.get(pk=1)

        entries = microsite_brand.entries.filter(
            Q(home_ordering__isnull=False) | Q(ordering__isnull=False))
        stores = microsite_brand.stores.all()

        products = [entry.product for entry in entries]
        Product.prefetch_specs(products)

        # ad-hoc logic for LG CL

        wtb_entities_dict = {
            wtb_entity.product: wtb_entity
            for wtb_entity in WtbEntity.objects.filter(
                brand=wtb_brand, product__isnull=False, is_active=True
            ).select_related('product', 'category', 'brand').order_by('-pk')
        }

        entities = Entity.objects.filter(
            product__in=products,
            store__in=stores,
            condition='https://schema.org/NewCondition',
            active_registry__cell_monthly_payment__isnull=True,
            seller__isnull=True
        ).get_available().order_by('active_registry__offer_price')

        entities_dict = OrderedDict()

        for entry in entries:
            entities_dict[entry.product] = []

        for entity in entities:
            entities_dict[entity.product].append(entity)

        result_array = [{
            'metadata': entry,
            'product': entry.product,
            'entities': entities_dict[entry.product],
            'wtb_entity': wtb_entities_dict.get(entry.product, None)
        } for entry in entries]

        serializer = MicrositeEntrySiteSerializer(
            result_array, many=True, context={'request': request})

        result = serializer.data

        return Response(result)


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
