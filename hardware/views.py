from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from hardware.models import Budget
from hardware.pagination import BudgetPagination
from hardware.serializers import BudgetSerializer


class BudgetViewSet(viewsets.ModelViewSet):
    queryset = Budget.objects.all()
    serializer_class = BudgetSerializer
    pagination_class = BudgetPagination
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Budget.objects.none()
        elif user.is_superuser:
            return Budget.objects.select_related('user').prefetch_related(
                'products_pool__instance_model')
        else:
            return user.budgets.select_related('user').prefetch_related(
                'products_pool__instance_model')
