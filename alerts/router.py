from rest_framework import routers

from alerts.views import AnonymousAlertViewSet, UserAlertViewSet

router = routers.SimpleRouter()
router.register(r'anonymous_alerts', AnonymousAlertViewSet)
router.register(r'user_alerts', UserAlertViewSet)
