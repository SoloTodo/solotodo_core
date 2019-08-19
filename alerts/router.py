from rest_framework import routers

from alerts.views import AnonymousAlertViewSet, UserAlertViewSet, \
    ProductPriceAlertViewSet

router = routers.SimpleRouter()
router.register(r'anonymous_alerts', AnonymousAlertViewSet)
router.register(r'user_alerts', UserAlertViewSet)
router.register(r'alerts', ProductPriceAlertViewSet)
