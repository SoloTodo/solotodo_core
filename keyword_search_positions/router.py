from rest_framework import routers

from keyword_search_positions.views import KeywordSearchViewSet, \
    KeywordSearchUpdateViewSet, KeywordSearchEntityPositionViewSet

router = routers.SimpleRouter()
router.register(r'keyword_searches', KeywordSearchViewSet)
router.register(r'keyword_search_updates', KeywordSearchUpdateViewSet)
router.register(r'keyword_search_entity_positions',
                KeywordSearchEntityPositionViewSet)
