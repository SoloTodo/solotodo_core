from rest_framework import routers

from banners.views import BannerViewSet, BannerUpdateViewSet, \
    BannerAssetViewSet

router = routers.SimpleRouter()
router.register(r'banners', BannerViewSet)
router.register(r'banner_updates', BannerUpdateViewSet)
router.register(r'banner_assets', BannerAssetViewSet)
