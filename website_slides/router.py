from rest_framework import routers

from website_slides.views import WebsiteSlideViewSet

router = routers.SimpleRouter()
router.register(r'website_slides', WebsiteSlideViewSet)
