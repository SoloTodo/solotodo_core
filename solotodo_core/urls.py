"""solotodo_core URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from allauth.socialaccount.providers.facebook.views import \
    FacebookOAuth2Adapter
from django.conf.urls import url, include
from django.contrib import admin
from rest_auth.registration.views import SocialLoginView
from rest_framework.authtoken.views import obtain_auth_token
from solotodo.router import router as solotodo_router
from category_templates.router import router as category_templates_router
from category_specs_forms.router import router as category_specs_forms_router
from reports.router import router as reports_router
from wtb.router import router as wtb_router
from category_columns.router import router as category_columns_router
from notebooks.router import router as notebooks_router
from hardware.router import router as hardware_router
from carousel_slides.router import router as carousel_slides_router
from alerts.router import router as alerts_router
from banners.router import router as banners_router
from product_lists.router import router as product_lists_router
from brand_comparisons.router import router as brand_comparisons_router
from entity_positions.router import router as entity_positions_router
from .custom_default_router import CustomDefaultRouter

router = CustomDefaultRouter()
router.extend(solotodo_router)
router.extend(category_templates_router)
router.extend(category_specs_forms_router)
router.extend(reports_router)
router.extend(wtb_router)
router.extend(category_columns_router)
router.extend(notebooks_router)
router.extend(hardware_router)
router.extend(carousel_slides_router)
router.extend(alerts_router)
router.extend(banners_router)
router.extend(product_lists_router)
router.extend(brand_comparisons_router)
router.extend(entity_positions_router)


class FacebookLogin(SocialLoginView):
    adapter_class = FacebookOAuth2Adapter


urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^accounts/', include('allauth.urls')),
    url(r'^metamodel/', include('metamodel.urls')),
    url(r'^api-auth/', include('rest_framework.urls')),
    url(r'^rest-auth/', include('rest_auth.urls')),
    url(r'^rest-auth/registration/', include('rest_auth.registration.urls')),
    url(r'^rest-auth/facebook/$', FacebookLogin.as_view(), name='fb_login'),
    url(r'^obtain-auth-token/$', obtain_auth_token),
    url(r'^', include(router.urls)),
    url(r'^', include('django.contrib.auth.urls')),
]
