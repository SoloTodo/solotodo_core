from django.core.exceptions import ValidationError
from django.db import models
from datetime import timedelta
from django.utils import timezone

from .alert import Alert


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

        def extract_price(entity_history, pricing_type):
            if entity_history:
                return getattr(entity_history, '{}_price'.format(pricing_type))
            else:
                return None

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
            AlertNotification.objects.create(
                alert=self,
                previous_normal_price_registry=previous_normal_price_registry,
                previous_offer_price_registry=previous_offer_price_registry
            ).send_email(self.email)

    def clean(self):
        if AnonymousAlert.objects.filter(email=self.email,
                                         alert__product=self.alert.product):
            raise ValidationError('email/product combination not unique')

    def save(self, *args, **kwargs):
        self.clean()
        super(AnonymousAlert, self).save(*args, **kwargs)

    class Meta:
        app_label = 'alerts'
        ordering = ('alert',)
