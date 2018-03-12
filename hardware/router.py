from rest_framework import routers

from hardware.views import BudgetViewSet, BudgetEntryViewSet, \
    VideoCardGpuViewSet

router = routers.SimpleRouter()
router.register(r'budgets', BudgetViewSet)
router.register(r'budget_entries', BudgetEntryViewSet)
router.register(r'videocard_gpus', VideoCardGpuViewSet,
                base_name='videocard_gpus')
