from django.contrib.auth import get_user_model
from rest_framework import viewsets, serializers, permissions
from rest_framework.decorators import detail_route, list_route
from rest_framework.response import Response

from solotodo.models import Store


class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ('email', 'is_staff', 'is_superuser')


class UserViewSet(viewsets.GenericViewSet):
    permission_classes = (permissions.IsAuthenticated,)

    @list_route()
    def me(self, request):
        return Response(UserSerializer(
            request.user,
            context={'request': request}).data)


class StoreSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Store
        fields = ('id', 'name')


class StoreViewSet(viewsets.ModelViewSet):
    queryset = Store.objects.all()
    serializer_class = StoreSerializer

