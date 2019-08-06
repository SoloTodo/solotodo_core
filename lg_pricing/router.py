from rest_framework import routers

from lg_pricing.views import LgWtbViewSet

router = routers.SimpleRouter()
router.register('lg_pricing', LgWtbViewSet, base_name='lg_pricing')
