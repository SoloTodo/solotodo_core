from decimal import Decimal
from django.conf import settings
from django.core.mail import send_mail
from django.db import models
from django.db.models import Count
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
    preferred_language = models.ForeignKey(Language, on_delete=models.CASCADE,
                                           blank=True, null=True)
    preferred_currency = models.ForeignKey(Currency, on_delete=models.CASCADE,
                                           blank=True, null=True)
    preferred_country = models.ForeignKey(
        Country, on_delete=models.CASCADE, blank=True, null=True)
    preferred_number_format = models.ForeignKey(
        NumberFormat, on_delete=models.CASCADE, blank=True, null=True)
    preferred_store = models.ForeignKey(
        Store, on_delete=models.CASCADE, blank=True, null=True,
        related_name='+'
    )
    preferred_stores = models.ManyToManyField(
        Store,
        blank=True,
        related_name='+')

    permissions = property(lambda self: sorted(self.get_all_permissions()))

    objects = EmailUserManager.from_queryset(SoloTodoUserQuerySet)()

    BOT_CACHE = None

    @property
    def name(self):
        return self.email

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

    def staff_summary(self, start_date, end_date):
        from solotodo.models import Entity, Product, CategoryTier
        from wtb.models import WtbEntity

        result = {}

        total_amount = Decimal(0)

        # Entities

        association_amount = settings.ENTITY_ASSOCIATION_AMOUNT

        associated_entities_count = Entity.objects.filter(
            last_association__gte=start_date,
            last_association__lte=end_date,
            last_association_user=self
        ).count()

        entities_total_amount = association_amount * associated_entities_count
        total_amount += entities_total_amount

        result['entities'] = {
            'count': associated_entities_count,
            'individual_amount': str(association_amount),
            'total_amount': str(entities_total_amount)
        }

        # WTB Entities

        wtb_association_amount = settings.WTB_ENTITY_ASSOCIATION_AMOUNT

        associated_wtb_entities_count = WtbEntity.objects.filter(
            last_association__gte=start_date,
            last_association__lte=end_date,
            last_association_user=self
        ).count()

        wtb_entities_total_amount = \
            wtb_association_amount * associated_wtb_entities_count
        total_amount += wtb_entities_total_amount

        result['wtb_entities'] = {
            'count': associated_wtb_entities_count,
            'individual_amount': str(wtb_association_amount),
            'total_amount': str(wtb_entities_total_amount)
        }

        # Products

        created_products_per_category = Product.objects.filter(
            creation_date__gte=start_date,
            creation_date__lte=end_date,
            creator=self
        ).values('instance_model__model__category__tier') \
            .annotate(c=Count('pk')).order_by()

        created_products_per_category_dict = {
            e['instance_model__model__category__tier']: e['c']
            for e in created_products_per_category
        }

        result['products'] = []

        for tier in CategoryTier.objects.all():
            created_products_count = created_products_per_category_dict.get(
                tier.pk, 0)

            tier_total_amount = \
                tier.creation_payment_amount * created_products_count
            total_amount += tier_total_amount

            result['products'].append({
                'tier': str(tier),
                'count': created_products_count,
                'individual_amount': str(tier.creation_payment_amount),
                'total_amount': str(tier_total_amount)
            })

        result['total_amount'] = str(total_amount)

        return result

    def staff_actions(self, start_date, end_date):
        from solotodo.models import EntityLog, Product
        from wtb.models import WtbEntity

        result = {}

        # Entity actions

        logs = EntityLog.objects\
            .filter(user=self,
                    creation_date__gte=start_date,
                    creation_date__lte=end_date)\
            .order_by('-creation_date') \
            .select_related('entity')

        result['entities'] = [{'id': log.id,
                               'entity_id': log.entity.id,
                               'name': log.entity.name,
                               'date': log.creation_date} for log in logs]

        # WtbEntity actions

        wtb_entities = WtbEntity.objects\
            .filter(last_association_user=self,
                    last_association__gte=start_date,
                    last_association__lte=end_date)\
            .order_by('-last_association')

        result['wtb_entities'] = [{'id': e.id,
                                   'name': e.name,
                                   'date': e.last_association}
                                  for e in wtb_entities]

        # Created products

        products = Product.objects\
            .filter(creator=self,
                    creation_date__gte=start_date,
                    creation_date__lte=end_date)\
            .order_by('-creation_date')\
            .select_related('instance_model')
        result['products'] = [{'id': p.id,
                               'name': str(p),
                               'date': p.creation_date}
                              for p in products]

        return result

    class Meta:
        app_label = 'solotodo'
        verbose_name = 'SoloTodo User'
        verbose_name_plural = 'SoloTodo Users'
        ordering = ('-date_joined',)
        permissions = (
            ('view_users',
             'Can view all users'),
            ('view_users_with_staff_actions',
             'Can view users with that have executed staff actions'),
            ('backend_list_users', 'Can view user list in backend'),
        )
