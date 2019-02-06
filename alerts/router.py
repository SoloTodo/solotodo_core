from rest_framework import routers

from alerts.views import AnonymousAlertViewSet

router = routers.SimpleRouter()
router.register(r'anonymous_alerts', AnonymousAlertViewSet)
