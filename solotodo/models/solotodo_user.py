from django.conf import settings
from django.core.mail import send_mail
from django.db import models
from django.template.loader import render_to_string
from django.utils import translation, timezone
from django.utils.translation import ugettext_lazy as _
from custom_user.models import AbstractEmailUser, EmailUserManager

from .number_format import NumberFormat
from .country import Country
from .currency import Currency
from .language import Language
from .store import Store


class SoloTodoUserQuerySet(models.QuerySet):
    def filter_with_staff_actions(self):
        return self.exclude(entity__isnull=True, product__isnull=True)


class SoloTodoUser(AbstractEmailUser):
    first_name = models.CharField(_('first name'), max_length=30, blank=True,
                                  null=True)
    last_name = models.CharField(_('last name'), max_length=30, blank=True,
                                 null=True)
    preferred_language = models.ForeignKey(Language, blank=True, null=True)
    preferred_currency = models.ForeignKey(Currency, blank=True, null=True)
    preferred_country = models.ForeignKey(
        Country, default=settings.DEFAULT_COUNTRY)
    preferred_number_format = models.ForeignKey(
        NumberFormat, blank=True, null=True)
    preferred_store = models.ForeignKey(
        Store, blank=True, null=True,
    )

    permissions = property(lambda self: sorted(self.get_all_permissions()))

    objects = EmailUserManager.from_queryset(SoloTodoUserQuerySet)()

    BOT_CACHE = None

    @classmethod
    def get_bot(cls):
        if not cls.BOT_CACHE:
            cls.BOT_CACHE = cls.objects.get(email=settings.BOT_USERNAME)
        return cls.BOT_CACHE

    def get_full_name(self):
        if not self.first_name and not self.last_name:
            return None

        first_name = self.first_name or ''
        last_name = self.last_name or ''

        return '{} {}'.format(first_name, last_name).strip()

    def email_recipient_text(self):
        full_name = self.get_full_name()
        if full_name:
            return '{} <{}>'.format(full_name, self.email)
        else:
            return self.email

    def preferred_currency_or_default(self):
        if self.preferred_currency:
            return self.preferred_currency
        else:
            return Currency.get_default()

    def send_entity_update_failure_email(self, entity, request_user,
                                         traceback):
        if self.preferred_language:
            email_language = self.preferred_language.code
        else:
            email_language = settings.LANGUAGE_CODE

        sender = SoloTodoUser().get_bot().email_recipient_text()
        translation.activate(email_language)

        email_recipients = [self.email_recipient_text()]

        html_message = render_to_string(
            'mailing/entity_pricing_update_failure.html', {
                'entity': entity,
                'request_user': request_user,
                'timestamp': timezone.now(),
                'host': settings.BACKEND_HOST,
                'error': traceback
            })

        subject = _('Error updating entity')

        send_mail('{} {}'.format(subject, entity.id),
                  'Error', sender, email_recipients,
                  html_message=html_message)

    def send_entity_dissociation_mail(self, entity, dissociation_user,
                                      reason=None):
        if self.preferred_language:
            email_language = self.preferred_language.code
        else:
            email_language = settings.LANGUAGE_CODE

        sender = SoloTodoUser().get_bot().email_recipient_text()
        translation.activate(email_language)

        if self.email != 'vj@solotodo.com':
            raise Exception('Not my email!')
        email_recipients = [self.email_recipient_text()]

        html_message = render_to_string(
            'mailing/entity_dissociation.html', {
                'entity': entity,
                'reason': reason,
                'dissociation_user': dissociation_user,
                'timestamp': timezone.now(),
                'host': settings.BACKEND_HOST,
            })

        subject = _('Entity dissociated')

        send_mail('{} - {}'.format(subject, entity.name),
                  'Error', sender, email_recipients,
                  html_message=html_message)

    class Meta:
        app_label = 'solotodo'
        verbose_name = 'SoloTodo User'
        verbose_name_plural = 'SoloTodo Users'
        ordering = ('-date_joined',)
        permissions = (
            ('view_users',
             'Can view all users'),
            ('view_users_with_staff_actions',
             'Can view users with that have executed staff actions')
        )
