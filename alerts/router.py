from rest_framework import routers

from alerts.views import ProductPriceAlertViewSet

router = routers.SimpleRouter()
router.register(r'alerts', ProductPriceAlertViewSet)
