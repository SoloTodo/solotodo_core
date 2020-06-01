from rest_framework import routers

from microsite.views import MicrositeBrandViewSet, MicrositeEntryViewset

router = routers.SimpleRouter()
router.register(r'microsite/brands', MicrositeBrandViewSet)
router.register(r'microsite/entries', MicrositeEntryViewset)
