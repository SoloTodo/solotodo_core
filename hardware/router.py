from rest_framework import routers

from hardware.views import BudgetViewSet, BudgetEntryViewSet

router = routers.SimpleRouter()
router.register(r'budgets', BudgetViewSet)
router.register(r'budget_entries', BudgetEntryViewSet)
