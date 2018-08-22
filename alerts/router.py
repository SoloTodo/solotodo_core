from rest_framework import routers

from alerts.views import AlertViewSet

router = routers.SimpleRouter()
router.register(r'alerts', AlertViewSet)
