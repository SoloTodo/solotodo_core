from rest_framework import routers

from wtb.views import WtbBrandViewSet, WtbEntityViewSet, \
    WtbBrandUpdateLogViewSet

router = routers.SimpleRouter()
router.register('wtb/brands', WtbBrandViewSet)
router.register('wtb/entities', WtbEntityViewSet)
router.register('wtb/brand_update_logs', WtbBrandUpdateLogViewSet)
