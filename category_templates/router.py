from rest_framework import routers

from category_templates.views import CategoryTemplatePurposeViewSet, \
    CategoryTemplateViewSet

router = routers.SimpleRouter()
router.register('category_template_purposes', CategoryTemplatePurposeViewSet)
router.register('category_templates', CategoryTemplateViewSet)
