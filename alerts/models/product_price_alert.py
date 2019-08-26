from django.db import models

from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.core import signing
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from django.utils import timezone
from django.conf import settings

from collections import OrderedDict
from datetime import timedelta
from decimal import Decimal

from solotodo.models import Product, Store, Entity, SoloTodoUser
from .utils import extract_price, calculate_price_delta, \
    currency_formatter, currency_formatter_no_symbol


class ProductPriceAlert(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    stores = models.ManyToManyField(Store)
    user = models.ForeignKey(
        get_user_model(), on_delete=models.CASCADE, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    active_history = models.ForeignKey(
        "ProductPriceAlertHistory", on_delete=models.SET_NULL,
        blank=True, null=True)

    creation_date = models.DateTimeField(auto_now_add=True)

    def get_entities(self):
        return Entity.objects.filter(
            product=self.product, store__in=self.stores.all())\
            .order_by('active_registry__offer_price').get_available()

    def update_active_history(self):
        from alerts.models import ProductPriceAlertHistory

        entries = []
        entities = self.get_entities()

        for entity in entities:
            entries.append(entity.active_registry)

        history = ProductPriceAlertHistory(alert=self)
        history.save()
        history.entries.set(entries)
        history.save()

        self.active_history = history
        self.save()

    def generate_delta_dict(self):
        entries = self.active_history.entries.all()
        entities = self.get_entities()

        delta_dict = OrderedDict()

        for entity in entities:
            delta_dict[entity.id] = {
                "active": entity.active_registry
            }

        for entry in entries:
            if entry.entity.id in delta_dict:
                delta_dict[entry.entity.id]['previous'] = entry
            else:
                delta_dict[entry.entity.id] = {
                    "previous": entry
                }

        return delta_dict

    def generate_minimum_dict(self):
        entries = self.active_history.entries.all()
        entities = self.get_entities()

        minimum_dict = {
            'offer': {
                'previous': None,
                'current': None
            },
            'normal': {
                'previous': None,
                'current': None
            }
        }

        if entries:
            min_offer_entry = min(entries, key=lambda x: x.offer_price)
            min_normal_entry = min(entries, key=lambda x: x.normal_price)

            minimum_dict['offer']['previous'] = min_offer_entry
            minimum_dict['normal']['previous'] = min_normal_entry

        if entities:
            min_offer_entry = min(
                entities,
                key=lambda x: x.active_registry.offer_price).active_registry

            min_normal_entry = min(
                entities,
                key=lambda x: x.active_registry.normal_price).active_registry

            minimum_dict['offer']['current'] = min_offer_entry
            minimum_dict['normal']['current'] = min_normal_entry

        return minimum_dict

    def check_for_changes(self):
        changed = False

        if self.user:
            delta_dict = self.generate_delta_dict()

            for key, value in delta_dict.items():
                previous = value.get('previous')
                current = value.get('active')

                if not previous or not current or \
                        previous.offer_price != current.offer_price or \
                        previous.normal_price != current.normal_price:
                    changed = True
                    break

            if changed:
                self.send_email(delta_dict)
                self.update_active_history()

        else:
            minimum_dict = self.generate_minimum_dict()

            previous_normal_price = extract_price(
                minimum_dict['normal']['previous'], 'normal')
            previous_offer_price = extract_price(
                minimum_dict['offer']['previous'], 'offer')
            new_normal_price = extract_price(
                minimum_dict['normal']['current'], 'normal')
            new_offer_price = extract_price(
                minimum_dict['offer']['current'], 'offer')

            last_interaction = self.active_history.timestamp

            if previous_normal_price != new_normal_price or \
                    previous_offer_price != new_offer_price or \
                    (timezone.now() - last_interaction) > timedelta(days=7):
                self.send_email(minimum_dict)
                self.update_active_history()

    def send_email(self, a_dict=None):
        if self.user:
            self._send_full_email(a_dict)
        else:
            self._send_minimum_email(a_dict)

    def _send_full_email(self, delta_dict=None):
        if not delta_dict:
            delta_dict = self.generate_delta_dict()

        def product_row(previous_entry, current_entry):
            row = '<tr class="price-table-row">' \
                  '<td class="text-cell"><a href={}>{}</a></td>' \
                  '<td class="{} price-cell">{}</td>' \
                  '<td class="{} price-cell">{}</td>' \
                  '</tr>'

            domain = Site.objects.get(
                pk=settings.SOLOTODO_PRICING_SITE_ID).domain

            if current_entry:
                entity = current_entry.entity
                store_name = current_entry.entity.store.name
            else:
                entity = previous_entry.entity
                store_name = previous_entry.entity.store.name

            store_sku_url = 'https://{}/skus/{}'
            previous_normal_price = extract_price(previous_entry, 'normal')
            previous_offer_price = extract_price(previous_entry, 'offer')
            new_normal_price = extract_price(current_entry, 'normal')
            new_offer_price = extract_price(current_entry, 'offer')

            normal_class = ""
            offer_class = ""
            normal_price_label = ""
            offer_price_label = ""

            if not previous_normal_price:
                normal_price_label = '<span class="old-price">' \
                                     'No Disponible</span><br/>' \
                                     '<span>{}</span>'\
                    .format(currency_formatter_no_symbol(new_normal_price))
                normal_class = "text-green"

            elif not new_normal_price:
                normal_price_label = '<span class="old-price">{}</span><br/>'\
                                     '<span>No Disponible</span>'\
                    .format(currency_formatter_no_symbol(
                        previous_normal_price))
                normal_class = "text-red"
            else:
                if new_normal_price == previous_normal_price:
                    normal_price_label = '<span>{}</span>'.format(
                        currency_formatter_no_symbol(new_normal_price))
                    normal_class = "text-grey"

                if new_normal_price < previous_normal_price:
                    normal_price_label = '<span class="old-price">{}</span>' \
                                         '<br/>' \
                                         '<span>{}</span>' \
                        .format(
                            currency_formatter_no_symbol(
                                previous_normal_price),
                            currency_formatter_no_symbol(new_normal_price))
                    normal_class = "text-green"

                if new_normal_price > previous_normal_price:
                    normal_price_label = '<span class="old-price">{}</span>' \
                                         '<br/>' \
                                         '<span>{}</span>'\
                        .format(
                            currency_formatter_no_symbol(
                                previous_normal_price),
                            currency_formatter_no_symbol(new_normal_price))
                    normal_class = "text-red"

            if not previous_offer_price:
                offer_price_label = '<span class="old-price">' \
                                    'No Disponible</span><br/>' \
                                    '<span>{}</span>'\
                    .format(currency_formatter_no_symbol(new_offer_price))
                offer_class = "text-green"

            elif not new_offer_price:
                offer_price_label = '<span class="old-price">{}</span><br/>' \
                                    '<span>No Disponible</span>' \
                    .format(currency_formatter_no_symbol(
                        previous_offer_price))
                offer_class = "text-red"

            else:
                if new_offer_price == previous_offer_price:
                    offer_price_label = '<span>{}</span>'.format(
                        currency_formatter_no_symbol(new_offer_price))
                    offer_class = "text-grey"

                if new_offer_price < previous_offer_price:
                    offer_price_label = '<span class="old-price">{}</span>' \
                                        '<br/>'\
                                        '<span>{}</span>' \
                        .format(
                            currency_formatter_no_symbol(previous_offer_price),
                            currency_formatter_no_symbol(new_offer_price))
                    offer_class = "text-green"
                if new_offer_price > previous_offer_price:
                    offer_price_label = '<span class="old-price">{}</span>' \
                                        '<br/>' \
                                        '<span>{}</span>' \
                        .format(
                            currency_formatter_no_symbol(previous_offer_price),
                            currency_formatter_no_symbol(new_offer_price))
                    offer_class = "text-red"

            return row.format(
                store_sku_url.format(domain, entity.id),
                store_name,
                normal_class,
                normal_price_label,
                offer_class,
                offer_price_label)

        html_rows = ''
        for key, value in delta_dict.items():
            previous = value.get('previous')
            current = value.get('active')
            html_rows += product_row(previous, current)

        product_label = '<span class="product-name">{}</span>'\
            .format(self.product)

        summary = 'Se han detectado cambios para el producto {}.'\
            .format(product_label)

        sender = SoloTodoUser().get_bot().email_recipient_text()

        html_message = render_to_string(
            'product_price_alert_mail.html',
            {
                'unsubscribe_key': signing.dumps({
                    'alert_id': self.id
                }),
                'product': self.product,
                'summary': mark_safe(summary),
                'table_content': mark_safe(html_rows),
                'api_host': settings.PUBLICAPI_HOST,
                'solotodo_com_domain': Site.objects.get(
                    pk=settings.SOLOTODO_PRICING_SITE_ID).domain
            })

        send_mail('Actualización de tu producto {}'.format(self.product),
                  summary, sender, [self.user.email],
                  html_message=html_message)
            
    def _send_minimum_email(self, minimum_dict=None):
        if not minimum_dict:
            minimum_dict = self.generate_minimum_dict()

        previous_normal_price = extract_price(
            minimum_dict['normal']['previous'], 'normal')
        previous_offer_price = extract_price(
            minimum_dict['offer']['previous'], 'offer')
        new_normal_price = extract_price(
            minimum_dict['normal']['current'], 'normal')
        new_offer_price = extract_price(
            minimum_dict['offer']['current'], 'offer')

        normal_price_delta = calculate_price_delta(
            previous_normal_price, new_normal_price)
        offer_price_delta = calculate_price_delta(
            previous_offer_price, new_offer_price)

        zero = Decimal(0)

        def price_labeler(previous_price, new_price, price_delta):
            if price_delta is None:
                return '<span class="text-grey">No disponible</span>'
            elif price_delta == Decimal('-Inf'):
                return \
                    '<span class="text-red"><span class="old-price">{}' \
                    '</span> No disponible</span>'.format(
                        currency_formatter(previous_price))
            elif price_delta == Decimal('Inf'):
                return \
                    '<span class="text-green"><span class="old-price"> ' \
                    'No disponible</span>{}</span>'.format(
                        currency_formatter(new_price))
            elif price_delta < zero:
                return \
                    '<span class="text-green"><span class="old-price">' \
                    '{}</span> ↘ {}</span>'.format(
                        currency_formatter(previous_price),
                        currency_formatter(new_price))
            elif price_delta == zero:
                return \
                    '<span class="text-grey">{}</span>'.format(
                        currency_formatter(previous_price))
            else:
                return \
                    '<span class="text-red"><span class="old-price">' \
                    '{}</span> ↗ {}</span>'.format(
                        currency_formatter(previous_price),
                        currency_formatter(new_price))

        offer_price_label = price_labeler(
            previous_offer_price, new_offer_price, offer_price_delta)
        normal_price_label = price_labeler(
            previous_normal_price, new_normal_price, normal_price_delta)

        product_label = '<span class="product-name">{}</span>'\
            .format(self.product)

        if offer_price_delta is None or \
                (offer_price_delta == zero and normal_price_delta == zero):
            summary = 'Sólo te queríamos contar que tu producto {} no ha ' \
                      'tenido cambios durante la última semana.'\
                .format(product_label)
        elif offer_price_delta == Decimal('-Inf'):
            summary = '¡Tu producto {} ya no está disponible! 😱.'\
                .format(product_label)
        elif offer_price_delta == Decimal('Inf'):
            summary = '¡Tu producto {} volvió a estar disponible! 😊'\
                .format(product_label)
        elif offer_price_delta < zero or normal_price_delta < zero:
            summary = '¡Tu producto {} bajó de precio! 😊'\
                .format(product_label)
        else:
            summary = '¡Tu producto {} subió de precio! 😞'\
                .format(product_label)

        sender = SoloTodoUser().get_bot().email_recipient_text()

        html_message = render_to_string(
            'alert_mail.html',
            {
                'unsubscribe_key': signing.dumps({
                    'alert_id': self.id
                }),
                'product': self.product,
                'summary': mark_safe(summary),
                'offer_price_label': mark_safe(offer_price_label),
                'normal_price_label': mark_safe(normal_price_label),
                'api_host': settings.PUBLICAPI_HOST,
                'solotodo_com_domain': Site.objects.get(
                    pk=settings.SOLOTODO_COM_SITE_ID).domain
            })

        send_mail('Actualización de tu producto {}'.format(self.product),
                  summary, sender, [self.email], html_message=html_message)

    class Meta:
        app_label = 'alerts'
        ordering = ('-creation_date',)
