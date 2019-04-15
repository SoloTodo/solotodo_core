from rest_framework import routers

from entity_positions.views import EntityPositionViewSet, \
    EntityPositionSectionViewSet

router = routers.SimpleRouter()
router.register(r'entity_positions', EntityPositionViewSet)
router.register(r'entity_position_sections', EntityPositionSectionViewSet)
