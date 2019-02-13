from rest_framework import routers

from banners.views import BannerViewSet

router = routers.SimpleRouter()
router.register(r'banners', BannerViewSet)
