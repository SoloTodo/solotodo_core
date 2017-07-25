import json

from rest_framework import viewsets, permissions
from rest_framework.decorators import list_route
from rest_framework.response import Response

from solotodo.models import Store, Language
from solotodo.serializers import UserSerializer, LanguageSerializer, \
    StoreSerializer


class UserViewSet(viewsets.GenericViewSet):
    permission_classes = (permissions.IsAuthenticated,)

    @list_route(methods=['get', 'patch'])
    def me(self, request):
        user = request.user

        if request.method == 'PATCH':
            content = json.loads(request.body.decode('utf-8'))
            language = Language.objects.get(pk=content['preferred_language'])
            user.preferred_language = language
            user.save()
        return Response(UserSerializer(
            user,
            context={'request': request}).data)


class LanguageViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Language.objects.all()
    serializer_class = LanguageSerializer


class StoreViewSet(viewsets.ModelViewSet):
    queryset = Store.objects.all()
    serializer_class = StoreSerializer

