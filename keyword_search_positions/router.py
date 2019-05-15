from rest_framework import routers

from keyword_search_positions.views import KeywordSearchViewSet

router = routers.SimpleRouter()
router.register(r'keyword_searches', KeywordSearchViewSet)