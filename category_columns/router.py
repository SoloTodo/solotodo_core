from rest_framework import routers

from category_columns.views import CategoryColumnViewSet

router = routers.SimpleRouter()
router.register('category_columns', CategoryColumnViewSet)
