from django.conf.urls import url, include
from rest_framework.authtoken.views import obtain_auth_token

# Serializers define the API representation.
from rest_framework import routers


# Routers provide an easy way of automatically determining the URL conf.
from solotodo.views import UserViewSet, StoreViewSet, LanguageViewSet, \
    CurrencyViewSet, CountryViewSet, StoreTypeViewSet, ProductTypeViewSet, \
    StoreUpdateLogViewSet

router = routers.DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'stores', StoreViewSet)
router.register(r'languages', LanguageViewSet)
router.register(r'store_types', StoreTypeViewSet)
router.register(r'currencies', CurrencyViewSet)
router.register(r'countries', CountryViewSet)
router.register(r'product_types', ProductTypeViewSet)
router.register(r'store_update_logs', StoreUpdateLogViewSet)

urlpatterns = [
    url(r'^api/', include(router.urls)),
    url(r'^api/obtain-auth-token/$', obtain_auth_token)
]
