from rest_framework import routers

from category_specs_forms.views import CategorySpecsFormLayoutViewset

router = routers.SimpleRouter()
router.register('category_specs_form_layouts', CategorySpecsFormLayoutViewset)
