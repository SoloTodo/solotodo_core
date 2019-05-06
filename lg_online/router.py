from rest_framework import routers

from lg_online.views import LgOnlineFeedViewSet

router = routers.SimpleRouter()
router.register('lg_online', LgOnlineFeedViewSet, base_name='lg_online')
