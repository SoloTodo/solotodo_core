from rest_framework import routers

from metamodel.views import MetaModelViewSet, InstanceModelViewSet, \
    MetaFieldViewSet, InstanceFieldViewSet

router = routers.SimpleRouter()
router.register(r'metamodel/meta_models', MetaModelViewSet)
router.register(r'metamodel/instance_models', InstanceModelViewSet)
router.register(r'metamodel/meta_fields', MetaFieldViewSet)
router.register(r'metamodel/instance_fields', InstanceFieldViewSet)
