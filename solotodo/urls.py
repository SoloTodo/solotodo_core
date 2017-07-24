from django.conf.urls import url, include
from rest_framework.authtoken.views import obtain_auth_token

# Serializers define the API representation.
from rest_framework import routers


# Routers provide an easy way of automatically determining the URL conf.
from solotodo.views import UserViewSet, StoreViewSet

router = routers.DefaultRouter()
router.register(r'users', UserViewSet, base_name='users')
router.register(r'stores', StoreViewSet)

urlpatterns = [
    url(r'^', include(router.urls)),
    url(r'^obtain-auth-token/$', obtain_auth_token)
]
