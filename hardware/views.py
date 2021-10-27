import urllib

from django.http import HttpResponseRedirect
from elasticsearch_dsl import Search
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from django_filters import rest_framework
from rest_framework.reverse import reverse

from hardware.filters import BudgetFilterSet
from hardware.forms.budget_export_format_form import BudgetExportFormatForm
from hardware.forms.budget_product_form import BudgetProductForm
from hardware.models import Budget, BudgetEntry
from hardware.pagination import BudgetPagination
from hardware.permissions import BudgetPermission
from hardware.serializers import BudgetSerializer, BudgetEntrySerializer
from solotodo.forms.product_form import ProductForm
from solotodo.forms.stores_form import StoresForm
from solotodo.models import Store


class BudgetViewSet(viewsets.ModelViewSet):
    queryset = Budget.objects.all()
    serializer_class = BudgetSerializer
    pagination_class = BudgetPagination
    permission_classes = (BudgetPermission,)
    filter_backends = (rest_framework.DjangoFilterBackend, )
    filter_class = BudgetFilterSet

    @action(methods=['post'], detail=True)
    def add_product(self, request, pk, *args, **kwargs):
        budget = self.get_object()

        form = ProductForm.from_user(request.user, request.data)
        if not form.is_valid():
            return Response(form.errors)

        product = form.cleaned_data['product']
        budget.products_pool.add(product)

        serializer = BudgetSerializer(budget, context={'request': request})
        return Response(serializer.data)

    @action(methods=['post'], detail=True)
    def select_cheapest_stores(self, request, pk, *args, **kwargs):
        budget = self.get_object()
        form = StoresForm.from_user(request.user, request.data)

        if not form.is_valid():
            return Response(form.errors)

        stores = form.cleaned_data['stores']
        if not stores:
            stores = Store.objects.filter_by_user_perms(
                request.user, 'view_store')

        budget.select_cheapest_stores(stores)

        updated_budget = self.get_object()
        serializer = BudgetSerializer(updated_budget,
                                      context={'request': request})

        return Response(serializer.data)

    @action(detail=True)
    def export(self, request, pk, *args, **kwargs):
        budget = self.get_object()

        form = BudgetExportFormatForm(request.query_params)
        if not form.is_valid():
            return Response(form.errors)

        export_format = form.cleaned_data['export_format']
        exported_budget = budget.export(export_format)

        return Response({'content': exported_budget})

    @action(detail=True)
    def compatibility_issues(self, request, pk, *args, **kwargs):
        budget = self.get_object()
        return Response(budget.compatibility_issues())

    @action(methods=['post'], detail=True)
    def remove_product(self, request, pk, *args, **kwargs):
        budget = self.get_object()
        form = BudgetProductForm.from_budget(budget, request.data)

        if not form.is_valid():
            return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)

        product = form.cleaned_data['product']
        budget.remove_product(product)

        budget = self.get_object()
        serializer = BudgetSerializer(budget, context={'request': request})
        return Response(serializer.data)

    @action(detail=True)
    def available_entities(self, request, *args, **kwargs):
        budget = self.get_object()
        query = {
            'ids': [p.id for p in budget.expanded_products_pool()],
            'stores': [s.id for s in budget.user.preferred_stores.all()]
        }

        if budget.user.preferred_exclude_refurbished:
            query['exclude_refurbished'] = 1

        url = reverse('product-available_entities', request=request) + '?' + \
            urllib.parse.urlencode(query, True)
        return HttpResponseRedirect(url)


class BudgetEntryViewSet(viewsets.ModelViewSet):
    queryset = BudgetEntry.objects.all()
    serializer_class = BudgetEntrySerializer
    pagination_class = BudgetPagination
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return BudgetEntry.objects.select_related(
                'budget', 'category',
                'selected_product__instance_model',
                'selected_store',
            )
        else:
            return BudgetEntry.objects.filter(
                budget__user=user
            ).select_related(
                'budget', 'category',
                'selected_product__instance_model',
                'selected_store',
            )


class VideoCardGpuViewSet(viewsets.ViewSet):
    def list(self, request, *args, **kwargs):
        search = Search(index='videocard-gpus')
        response = search[:1000].execute()
        serialized_result = [
            e['_source'] for e in response.to_dict()['hits']['hits']]
        return Response(serialized_result)

    def retrieve(self, request, pk=None, *args, **kwargs):
        search = Search(index='videocard-gpus')
        response = search.filter('term', id=pk).execute()

        if not response.hits:
            return Response(status=status.HTTP_404_NOT_FOUND)

        return Response(response.hits[0].to_dict())
