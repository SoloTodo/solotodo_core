from rest_framework import routers

from hardware.views import BudgetViewSet

router = routers.SimpleRouter()
router.register(r'budgets', BudgetViewSet)
