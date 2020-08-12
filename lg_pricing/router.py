from rest_framework import routers

from lg_pricing.views import LgWtbViewSet, SendinblueViewSet

router = routers.SimpleRouter()
router.register('lg_pricing', LgWtbViewSet, basename='lg_pricing')
router.register(
    'lg_pricing/sendinblue', SendinblueViewSet, basename='sendinblue')
