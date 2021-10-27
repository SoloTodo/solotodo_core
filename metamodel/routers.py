from rest_framework import routers

from metamodel.views import MetaModelViewSet, InstanceModelViewSet, \
    MetaFieldViewSet, InstanceFieldViewSet

router = routers.SimpleRouter()
router.register(r'metamodels/meta_models', MetaModelViewSet)
router.register(r'metamodels/instance_models', InstanceModelViewSet)
router.register(r'metamodels/meta_fields', MetaFieldViewSet)
router.register(r'metamodels/instance_fields', InstanceFieldViewSet)
