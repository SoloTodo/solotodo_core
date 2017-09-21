from django.conf.urls import url, include
from rest_framework.authtoken.views import obtain_auth_token

# Serializers define the API representation.
from rest_framework import routers


# Routers provide an easy way of automatically determining the URL conf.
from solotodo.views import UserViewSet, StoreViewSet, LanguageViewSet, \
    CurrencyViewSet, CountryViewSet, StoreTypeViewSet, CategoryViewSet, \
    StoreUpdateLogViewSet, EntityViewSet, ProductViewSet, \
    NumberFormatViewSet, EntityStateViewSet

router = routers.SimpleRouter()
router.register(r'users', UserViewSet)
router.register(r'stores', StoreViewSet)
router.register(r'number_formats', NumberFormatViewSet)
router.register(r'entity_states', EntityStateViewSet)
router.register(r'languages', LanguageViewSet)
router.register(r'store_types', StoreTypeViewSet)
router.register(r'currencies', CurrencyViewSet)
router.register(r'countries', CountryViewSet)
router.register(r'categories', CategoryViewSet)
router.register(r'store_update_logs', StoreUpdateLogViewSet)
router.register(r'entities', EntityViewSet)
router.register(r'products', ProductViewSet)
