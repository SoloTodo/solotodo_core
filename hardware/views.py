from rest_framework import viewsets
from rest_framework.decorators import detail_route
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from hardware.models import Budget, BudgetEntry
from hardware.pagination import BudgetPagination
from hardware.serializers import BudgetSerializer, BudgetEntrySerializer
from solotodo.forms.product_form import ProductForm


class BudgetViewSet(viewsets.ModelViewSet):
    queryset = Budget.objects.all()
    serializer_class = BudgetSerializer
    pagination_class = BudgetPagination
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Budget.objects.select_related('user').prefetch_related(
                'products_pool__instance_model',
                'entries__selected_product__instance_model'
                'entries__selected_store'
            )
        else:
            return user.budgets.select_related('user').prefetch_related(
                'products_pool__instance_model',
                'entries__selected_product__instance_model'
                'entries__selected_store'
            )

    @detail_route(methods=['post'])
    def add_product(self, request, pk, *args, **kwargs):
        budget = self.get_object()

        form = ProductForm.from_user(request.user, request.data)
        if not form.is_valid():
            return Response(form.errors)

        product = form.cleaned_data['product']
        budget.products_pool.add(product)

        serializer = BudgetSerializer(budget, context={'request': request})
        return Response(serializer.data)


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
