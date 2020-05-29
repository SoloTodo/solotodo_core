from rest_framework import routers

from microsite.views import MicrositeBrandViewSet

router = routers.SimpleRouter()
router.register(r'microsite_brands', MicrositeBrandViewSet)
