from allauth.account.adapter import DefaultAccountAdapter
from django.conf import settings
from django.contrib.sites.models import Site


class SoloTodoAccountAdapter(DefaultAccountAdapter):
    def send_confirmation_mail(self, request, emailconfirmation, signup):
        current_site = Site.objects.get(pk=settings.SOLOTODO_COM_SITE_ID)

        if 'origin' in request.headers:
            activation_domain = request.headers['origin']
        else:
            activation_domain = 'https://' + current_site.domain

        activate_url = '{}/account/verify-email?key={}'.format(
            activation_domain, emailconfirmation.key)

        ctx = {
            "user": emailconfirmation.email_address.user,
            "activate_url": activate_url,
            "current_site": current_site,
            "key": emailconfirmation.key,
        }

        if signup:
            email_template = 'account/email/email_confirmation_signup'
        else:
            email_template = 'account/email/email_confirmation'
        self.send_mail(email_template,
                       emailconfirmation.email_address.email,
                       ctx)
