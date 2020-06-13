from rest_framework import routers

from lg_pricing.views import LgWtbViewSet

router = routers.SimpleRouter()
router.register('lg_pricing', LgWtbViewSet, basename='lg_pricing')
