from django.conf.urls import url, include
from rest_framework.authtoken.views import obtain_auth_token

# Serializers define the API representation.
from rest_framework import routers


# Routers provide an easy way of automatically determining the URL conf.
from solotodo.views import UserViewSet, StoreViewSet, LanguageViewSet, \
    CurrencyViewSet, CountryViewSet, StoreTypeViewSet, ProductTypeViewSet, \
    StoreUpdateLogViewSet, EntityViewSet, ProductViewSet, \
    NumberFormatViewSet, EntityHistoryViewSet

router = routers.DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'stores', StoreViewSet)
router.register(r'number_formats', NumberFormatViewSet)
router.register(r'languages', LanguageViewSet)
router.register(r'store_types', StoreTypeViewSet)
router.register(r'currencies', CurrencyViewSet)
router.register(r'countries', CountryViewSet)
router.register(r'product_types', ProductTypeViewSet)
router.register(r'store_update_logs', StoreUpdateLogViewSet)
router.register(r'entities', EntityViewSet)
router.register(r'products', ProductViewSet)
router.register(r'entity_histories', EntityHistoryViewSet)

urlpatterns = [
    url(r'^api/', include(router.urls)),
    url(r'^api/api-auth/', include('rest_framework.urls')),
    url(r'^api/obtain-auth-token/$', obtain_auth_token)
]
