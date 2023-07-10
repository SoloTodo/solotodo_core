from urllib.parse import urlparse

from allauth.account.utils import user_pk_to_url_str
from dj_rest_auth.forms import default_url_generator
from dj_rest_auth.serializers import PasswordResetSerializer
from django.urls import reverse


def custom_url_generator(request, user, temp_key):
    if 'HTTP_REFERER' not in request.META:
        return default_url_generator(request, user, temp_key)

    path = reverse(
        'password_reset_confirm',
        args=[user_pk_to_url_str(user), temp_key],
    )

    referer_params = urlparse(request.META['HTTP_REFERER'])

    url = '{}://{}{}'.format(referer_params.scheme, referer_params.netloc, path)
    print(url)

    return url


class CustomPasswordResetSerializer(PasswordResetSerializer):
    def get_email_options(self):
        return {
            'url_generator': custom_url_generator,
        }
