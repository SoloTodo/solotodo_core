from rest_framework import status
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, \
    TokenObtainSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from solotodo.serializers import MyUserSerializer

# Refines the validation to pass the context to our custom serializer
# Also ignores the "UPDATE_LAST_LOGIN" setting of the library
class MyTokenObtainPairSerializer(TokenObtainSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)

        refresh = RefreshToken.for_user(self.user)
        serialized_user = MyUserSerializer(instance=self.user,
                                           context=self.context)

        refresh['user'] = serialized_user.data
        data['refresh'] = str(refresh)
        data['access'] = str(refresh.access_token)

        return data


# Customizes the Serializer class and passes the request context to the
# serializer so that it can be passed down to our own user serlializer
class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data,
                                         context={'request': request})

        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as e:
            raise InvalidToken(e.args[0])

        return Response(serializer.validated_data,
                        status=status.HTTP_200_OK)
