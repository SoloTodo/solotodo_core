from django.db.models import Q
from django_filters import rest_framework

from hardware.models import Budget


class BudgetFilterSet(rest_framework.FilterSet):
    ids = rest_framework.ModelMultipleChoiceFilter(
        queryset=Budget.objects.all(),
        method='_ids',
        label='Entities'
    )

    @classmethod
    def available_budgets(cls, user):
        budgets = Budget.objects.select_related('user').prefetch_related(
            'products_pool__instance_model',
            'entries__selected_product__instance_model',
            'entries__selected_store'
        )

        if user.is_superuser:
            return budgets

        filters = Q(is_public=True)

        if user.is_authenticated:
            filters |= Q(user=user)

        return budgets.filter(filters)

    @property
    def qs(self):
        qs = super(BudgetFilterSet, self).qs.select_related('user')\
            .prefetch_related(
                'products_pool__instance_model',
                'entries__selected_product__instance_model',
                'entries__selected_store'
            )

        if self.request:
            available_budgets = self.available_budgets(self.request.user)
            qs = qs & available_budgets

        return qs

    def _ids(self, queryset, name, value):
        if value:
            return queryset.filter(pk__in=[x.pk for x in value])
        return queryset

    class Meta:
        model = Budget
        fields = []
