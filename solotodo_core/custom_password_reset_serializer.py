from urllib.parse import urlparse
from rest_auth.serializers import PasswordResetSerializer


class CustomPasswordResetSerializer(PasswordResetSerializer):
    def get_email_options(self):
        request = self.context.get('request')

        if 'HTTP_REFERER' not in request.META:
            return {}

        referer_params = urlparse(request.META['HTTP_REFERER'])
        referer_domain = referer_params.netloc

        return {
            'domain_override': referer_domain,
            'use_https': referer_params.scheme == 'https',
            'html_email_template_name': 'registration/password_reset_email_html.html'
        }
