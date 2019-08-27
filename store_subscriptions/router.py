from rest_framework import routers

from store_subscriptions.views import StoreSubscriptionViewSet

router = routers.SimpleRouter()
router.register(r'store_subscriptions', StoreSubscriptionViewSet)
