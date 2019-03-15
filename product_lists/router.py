from rest_framework import routers

from product_lists.views import ProductListViewSet

router = routers.SimpleRouter()
router.register(r'product_lists', ProductListViewSet)
