from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.template.loader import render_to_string
from django.core import signing
from django.utils.safestring import mark_safe
from django.conf import settings
from django.contrib.sites.models import Site
from django.core.mail import send_mail

from .alert_notification import AlertNotification
from solotodo.models import Entity, SoloTodoUser
from .alert import Alert
from .utils import extract_price, calculate_price_delta, currency_formatter


class UserAlert(models.Model):
    alert = models.OneToOneField(Alert, on_delete=models.CASCADE)
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    entity = models.ForeignKey(Entity, on_delete=models.CASCADE,
                               null=True, blank=True)

    def __str__(self):
        return '{} - {} - {}'.format(self.alert, self.user, self.entity)

    def check_for_changes(self):
        previous_normal_price_registry = self.alert.normal_price_registry
        previous_offer_price_registry = self.alert.offer_price_registry

        if self.entity:
            self.alert.normal_price_registry = self.entity.active_registry
            self.alert.offer_price_registry = self.entity.active_registry
            self.alert.save()
        else:
            self.alert.update()

        previous_normal_price = extract_price(previous_normal_price_registry,
                                              'normal')
        previous_offer_price = extract_price(previous_offer_price_registry,
                                             'offer')
        new_normal_price = extract_price(self.alert.normal_price_registry,
                                         'normal')
        new_offer_price = extract_price(self.alert.offer_price_registry,
                                        'offer')

        if previous_normal_price != new_normal_price or \
                previous_offer_price != new_offer_price:
            alert_notification = AlertNotification.objects.create(
                alert=self.alert,
                previous_normal_price_registry=previous_normal_price_registry,
                previous_offer_price_registry=previous_offer_price_registry
            )

            self.send_email(alert_notification)

    def send_email(self, alert_notification):
        previous_normal_price = extract_price(
            alert_notification.previous_normal_price_registry, 'normal')
        previous_offer_price = extract_price(
            alert_notification.previous_offer_price_registry, 'offer')
        new_normal_price = extract_price(self.alert.normal_price_registry,
                                         'normal')
        new_offer_price = extract_price(self.alert.offer_price_registry,
                                        'offer')

        normal_price_delta = calculate_price_delta(previous_normal_price,
                                                   new_normal_price)
        offer_price_delta = calculate_price_delta(previous_offer_price,
                                                  new_offer_price)

        zero = Decimal(0)

        def price_labeler(previous_price, new_price, price_delta):
            if price_delta is None:
                return '<span class="text-grey">No disponible</span>'
            elif price_delta == Decimal('-Inf'):
                return \
                    '<span class="text-red"><span class="old-price">{}' \
                    '</span> No disponible</span>'.format(currency_formatter(
                        previous_price))
            elif price_delta == Decimal('Inf'):
                return \
                    '<span class="text-green"><span class="old-price"> ' \
                    'No disponible</span>{}</span>'.format(currency_formatter(
                        new_price))
            elif price_delta < zero:
                return \
                    '<span class="text-green"><span class="old-price">' \
                    '{}</span> ↘ {}</span>'.format(
                        currency_formatter(previous_price),
                        currency_formatter(new_price)
                    )
            elif price_delta > zero:
                return \
                    '<span class="text-red"><span class="old-price">' \
                    '{}</span> ↗ {}</span>'.format(
                        currency_formatter(previous_price),
                        currency_formatter(new_price)
                    )
            else:
                return \
                    '<span class="text-grey">{}</span>'.format(
                        currency_formatter(new_price)
                    )

        if self.entity:
            product = self.entity.product
        else:
            product = self.alert.product

        product_label = '<span class="product-name">{}</span>'.format(product)

        offer_price_label = price_labeler(
            previous_offer_price, new_offer_price, offer_price_delta)
        normal_price_label = price_labeler(
            previous_normal_price, new_normal_price, normal_price_delta)

        if offer_price_delta == Decimal('-Inf'):
            summary = 'El producto {} ya no está disponible'.format(
                product_label)
        elif offer_price_delta == Decimal('Inf'):
            summary = 'El producto {} volvió a estar disponible'.format(
                product_label)
        elif offer_price_delta < zero or normal_price_delta < zero:
            summary = 'El producto {} bajó de precio'.format(
                product_label)
        else:
            summary = 'El producto {} subió de precio'.format(
                product_label)

        sender = SoloTodoUser().get_bot().email_recipient_text()

        html_message = render_to_string(
            'user_alert_mail.html', {
                'unsubscribe_key': signing.dumps({
                    'anonymous_alert_id': self.id
                }),
                'product': product,
                'summary': mark_safe(summary),
                'offer_price_label': mark_safe(offer_price_label),
                'normal_price_label': mark_safe(normal_price_label),
                'api_host': settings.PUBLICAPI_HOST,
                'solotodo_com_domain': Site.objects.get(
                    pk=settings.SOLOTODO_PRICING_SITE_ID).domain
            })

        send_mail('Actualización del producto {}'.format(self.alert.product),
                  summary, sender, [self.user.email],
                  html_message=html_message)

    def clean(self):
        if not self.entity and not self.alert.product:
            raise ValidationError('Alert does not have a product '
                                  'nor an entity')

        if self.entity:
            if self.alert.product:
                raise ValidationError('Alert has both a product and an entity '
                                      '(only one should be defined)')
            if not self.entity.product:
                raise ValidationError('The entity is not associated '
                                      'with a product')

    def save(self, *args, **kwargs):
        self.clean()
        super(UserAlert, self).save(*args, **kwargs)

    class Meta:
        app_label = 'alerts'
        ordering = ('alert',)
