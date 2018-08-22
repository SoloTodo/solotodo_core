from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.mail import send_mail
from django.db import models
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.safestring import mark_safe

from solotodo.models import EntityHistory, Store, Product, Entity, SoloTodoUser
from solotodo.utils import format_currency


class Alert(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    normal_price_registry = models.ForeignKey(
        EntityHistory, blank=True, null=True, on_delete=models.CASCADE,
        related_name='+')
    offer_price_registry = models.ForeignKey(
        EntityHistory, blank=True, null=True, on_delete=models.CASCADE,
        related_name='+')
    email = models.EmailField()
    stores = models.ManyToManyField(Store)
    creation_date = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return '{} - {}'.format(self.product, self.email)

    @classmethod
    def find_optimum_entity_history(cls, product, stores, pricing_type):
        es = Entity.objects.filter(
            product=product, store__in=stores.all()).get_available().order_by(
            'active_registry__{}_price'.format(pricing_type))

        if es:
            return es[0].active_registry
        else:
            return None

    @classmethod
    def set_up(cls, product, stores, email):
        normal_price_registry = cls.find_optimum_entity_history(
            product, stores, 'normal')
        offer_price_registry = cls.find_optimum_entity_history(
            product, stores, 'offer')

        alert = cls.objects.create(
            product=product,
            normal_price_registry=normal_price_registry,
            offer_price_registry=offer_price_registry,
            email=email
        )

        alert.stores.set(stores)
        return alert

    def check_for_changes(self):
        new_normal_price_registry = self.find_optimum_entity_history(
            self.product, self.stores, 'normal')
        new_offer_price_registry = self.find_optimum_entity_history(
            self.product, self.stores, 'offer')

        previous_normal_price_registry = self.normal_price_registry
        previous_offer_price_registry = self.offer_price_registry

        # Update the alert pricing registry

        self.normal_price_registry = new_normal_price_registry
        self.offer_price_registry = new_offer_price_registry
        self.save()

        # Check whether to send an email notification

        def extract_price(entity_history, pricing_type):
            if entity_history:
                return getattr(entity_history, '{}_price'.format(pricing_type))
            else:
                return None

        previous_normal_price = extract_price(previous_normal_price_registry,
                                              'normal')
        previous_offer_price = extract_price(previous_offer_price_registry,
                                             'offer')
        new_normal_price = extract_price(new_normal_price_registry, 'normal')
        new_offer_price = extract_price(new_offer_price_registry, 'offer')

        notifications = self.notifications.order_by('-creation_date')
        if notifications:
            last_interaction = notifications[0].creation_date
        else:
            last_interaction = self.creation_date

        # Send a notification if the price has changed or if its been a week
        # since the last notification (even if the price hasn't changed)
        if (previous_normal_price != new_normal_price or
                previous_offer_price != new_offer_price or
                (timezone.now() - last_interaction) > timedelta(days=7)):
            AlertNotification.objects.create(
                alert=self,
                previous_normal_price_registry=previous_normal_price_registry,
                previous_offer_price_registry=previous_offer_price_registry
            ).send_email()

    class Meta:
        ordering = ('-creation_date', )


class AlertNotification(models.Model):
    alert = models.ForeignKey(Alert, on_delete=models.CASCADE,
                              related_name='notifications')
    previous_normal_price_registry = models.ForeignKey(
        EntityHistory, blank=True, null=True, on_delete=models.CASCADE,
        related_name='+')
    previous_offer_price_registry = models.ForeignKey(
        EntityHistory, blank=True, null=True, on_delete=models.CASCADE,
        related_name='+')
    creation_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return '{} - {}'.format(self.alert, self.creation_date)

    def send_email(self):
        def extract_price(entity_history, pricing_type):
            if entity_history:
                return getattr(entity_history, '{}_price'.format(pricing_type))
            else:
                return None

        def calculate_price_delta(previous_price, new_price):
            # Convention for the deltas calculation:
            # None: the product was unavailable, and it's still unavailable
            # -Inf: the product was available, but now is unavailable
            # negative value: the product lowered its price
            # 0: the product maintained its price
            # positive value: the product raised its price
            # +Inf: the product was unavailable, but now is available

            if new_price is None:
                if previous_price is None:
                    return None
                else:
                    return Decimal('-Inf')
            else:
                if previous_price is None:
                    return Decimal('Inf')
                else:
                    return new_price - previous_price

        def currency_formatter(value):
            return format_currency(value, places=0)

        previous_normal_price = extract_price(
            self.previous_normal_price_registry, 'normal')
        previous_offer_price = extract_price(
            self.previous_offer_price_registry, 'offer')
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
                      'tenido cambios durante la última semana.'.format(
                        product_label)
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
                'product': self.alert.product,
                'summary': mark_safe(summary),
                'offer_price_label': mark_safe(offer_price_label),
                'normal_price_label': mark_safe(normal_price_label),
                'api_host': settings.PUBLICAPI_HOST,
                'solotodo_com_domain': Site.objects.get(
                    pk=settings.SOLOTODO_COM_SITE_ID).domain
            })

        with open('email.html', 'w') as f:
            f.write(html_message)

        send_mail('Actualización de tu producto {}'.format(self.alert.product),
                  summary, sender, [self.alert.email],
                  html_message=html_message)

    class Meta:
        ordering = ('-creation_date', )
