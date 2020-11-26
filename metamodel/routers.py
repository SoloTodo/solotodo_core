from rest_framework import routers

from metamodel.views import MetaModelViewSet, InstanceModelViewSet, \
    MetaFieldViewSet

router = routers.SimpleRouter()
router.register(r'metamodels/models', MetaModelViewSet)
router.register(r'metamodels/instance', InstanceModelViewSet)
router.register(r'metamodels/metafield', MetaFieldViewSet)
