"""solotodo_core URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  re_path(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  re_path(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  re_path(r'^blog/', include('blog.urls'))
"""
from allauth.socialaccount.providers.facebook.views import \
    FacebookOAuth2Adapter
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from django.urls import include, re_path
from django.contrib import admin
from django.http import JsonResponse
from django.urls import path
from dj_rest_auth.registration.views import SocialLoginView
from rest_framework import permissions
from rest_framework.authtoken.views import obtain_auth_token
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView, \
    TokenObtainPairView
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
from brand_comparisons.router import router as brand_comparisons_router
from lg_pricing.router import router as lg_pricing_router
from keyword_search_positions.router import router as keyword_search_router
from store_subscriptions.router import router as store_subscription_router
from microsite.router import router as microsite_router
from .custom_default_router import CustomDefaultRouter
from metamodel.routers import router as metamodel_router
from website_slides.router import router as website_slides_router

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
router.extend(brand_comparisons_router)
router.extend(lg_pricing_router)
router.extend(keyword_search_router)
router.extend(store_subscription_router)
router.extend(microsite_router)
router.extend(metamodel_router)
router.extend(website_slides_router)


class FacebookLogin(SocialLoginView):
    adapter_class = FacebookOAuth2Adapter


class GoogleLogin(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter


class JwtTokens(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        token = RefreshToken.for_user(request.user)
        return JsonResponse({
            'access': str(token.access_token),
            'refresh': str(token)
        })


urlpatterns = [
    re_path(r'^admin/', admin.site.urls),
    re_path(r'^obtain-auth-token/$', obtain_auth_token),
    re_path(r'^accounts/', include('allauth.urls')),
    re_path(r'^metamodel/', include('metamodel.urls')),
    # re_path(r'^api-auth/', include('rest_framework.urls')),
    re_path(r'^auth/get_jwt_tokens/$', JwtTokens.as_view()),
    re_path(r'^rest-auth/', include('dj_rest_auth.urls')),
    re_path(r'^rest-auth/registration/', include(
        'dj_rest_auth.registration.urls')),
    re_path(r'^rest-auth/facebook/$', FacebookLogin.as_view(), name='fb_login'),
    re_path(r'^rest-auth/google/$', GoogleLogin.as_view()),
    path('auth/token/', TokenObtainPairView.as_view(),
         name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(),
         name='token_refresh'),
    re_path(r'^', include(router.urls)),
    re_path(r'^', include('django.contrib.auth.urls')),
]
