from rest_framework import routers

from carousel_slides.views import CarouselSlideViewSet

router = routers.SimpleRouter()
router.register('carousel_slides', CarouselSlideViewSet)
