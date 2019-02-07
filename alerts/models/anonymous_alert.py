from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from django.contrib.sites.models import Site
from django.core import signing
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

from .alert import Alert
from .utils import extract_price, calculate_price_delta, currency_formatter

from solotodo.models import SoloTodoUser


class AnonymousAlert(models.Model):
    alert = models.OneToOneField(Alert, on_delete=models.CASCADE)
    email = models.EmailField()

    def __str__(self):
        return '{} - {}'.format(self.alert, self.email)

    def check_for_changes(self):
        from .alert_notification import AlertNotification
        previous_normal_price_registry = self.alert.normal_price_registry
        previous_offer_price_registry = self.alert.offer_price_registry

        self.alert.update()

        # Check whether to send an email notification

        previous_normal_price = extract_price(previous_normal_price_registry,
                                              'normal')
        previous_offer_price = extract_price(previous_offer_price_registry,
                                             'offer')
        new_normal_price = extract_price(self.alert.normal_price_registry,
                                         'normal')
        new_offer_price = extract_price(self.alert.offer_price_registry,
                                        'offer')

        notifications = self.alert.notifications.order_by('-creation_date')
        if notifications:
            last_interaction = notifications[0].creation_date
        else:
            last_interaction = self.alert.creation_date

        # Send a notification if the price has changed or if its been a week
        # since the last notification (even if the price hasn't changed)
        if (previous_normal_price != new_normal_price or
                previous_offer_price != new_offer_price or
                (timezone.now() - last_interaction) > timedelta(days=7)):
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

        # We have 12 combinations
        # normal delta None and offer delta None
        # normal delta -Inf and offer delta -Inf
        # normal delta Inf and offer delta Inf
        # the 9 combinations of (neg, zero, pos) x (neg, zero, pos) for deltas

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
            elif price_delta == zero:
                return \
                    '<span class="text-grey">{}</span>'.format(
                        currency_formatter(previous_price),
                    )
            else:
                return \
                    '<span class="text-red"><span class="old-price">' \
                    '{}</span> ↗ {}</span>'.format(
                        currency_formatter(previous_price),
                        currency_formatter(new_price)
                    )

        offer_price_label = price_labeler(
            previous_offer_price, new_offer_price, offer_price_delta)
        normal_price_label = price_labeler(
            previous_normal_price, new_normal_price, normal_price_delta)

        product_label = '<span class="product-name">{}</span>'.format(
            self.alert.product)

        if offer_price_delta is None or \
                (offer_price_delta == zero and normal_price_delta == zero):
            summary = 'Sólo te queríamos contar que tu producto {} no ha ' \
                      'tenido cambios durante la última semana.'\
                .format(product_label)
        elif offer_price_delta == Decimal('-Inf'):
            summary = '¡Tu producto {} ya no está disponible! 😱.'.format(
                product_label)
        elif offer_price_delta == Decimal('Inf'):
            summary = '¡Tu producto {} volvió a estar disponible! 😊'.format(
                product_label)
        elif offer_price_delta < zero or normal_price_delta < zero:
            summary = '¡Tu producto {} bajó de precio! 😊'.format(
                product_label)
        else:
            summary = '¡Tu producto {} subió de precio! 😞'.format(
                product_label)

        sender = SoloTodoUser().get_bot().email_recipient_text()

        html_message = render_to_string(
            'alert_mail.html', {
                'unsubscribe_key': signing.dumps({
                    'anonymous_alert_id': self.id
                }),
                'product': self.alert.product,
                'summary': mark_safe(summary),
                'offer_price_label': mark_safe(offer_price_label),
                'normal_price_label': mark_safe(normal_price_label),
                'api_host': settings.PUBLICAPI_HOST,
                'solotodo_com_domain': Site.objects.get(
                    pk=settings.SOLOTODO_COM_SITE_ID).domain
            })

        send_mail('Actualización de tu producto {}'.format(self.alert.product),
                  summary, sender, [self.email],
                  html_message=html_message)

    def clean(self):
        if AnonymousAlert.objects.filter(email=self.email,
                                         alert__product=self.alert.product) \
                .exclude(pk=self.pk):
            raise ValidationError('email/product combination not unique')

    def save(self, *args, **kwargs):
        self.clean()
        super(AnonymousAlert, self).save(*args, **kwargs)

    class Meta:
        app_label = 'alerts'
        ordering = ('alert',)
