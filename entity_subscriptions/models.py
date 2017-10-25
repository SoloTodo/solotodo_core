from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db import models
from django.template.loader import render_to_string
from django.utils import translation, timezone
from django.utils.translation import ugettext_lazy as _

from solotodo.models import Entity, EntityHistory, SoloTodoUser


class EntitySubscription(models.Model):
    entity = models.ForeignKey(Entity)
    last_history_seen = models.ForeignKey(EntityHistory, blank=True, null=True)
    users = models.ManyToManyField(get_user_model())
    reference_price = models.DecimalField(max_digits=10, decimal_places=2)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.last_history_seen:
            return str(self.last_history_seen)
        else:
            return str(self.entity)

    def check_for_updates(self):
        self.entity.update_pricing()

        old_history = self.last_history_seen
        new_history = self.entity.active_registry

        old_is_available = old_history and old_history.is_available()
        new_is_available = new_history and new_history.is_available()

        send_notification_mail = False
        if old_is_available != new_is_available:
            send_notification_mail = True
        elif (old_is_available and new_is_available and (
                        old_history.normal_price != new_history.normal_price or
                        old_history.offer_price != new_history.offer_price)):
            send_notification_mail = True

        if send_notification_mail:
            print('Sending mail ')
            for user in self.users.all():
                if user.preferred_language:
                    email_language = user.preferred_language.code
                else:
                    email_language = settings.LANGUAGE_CODE

                sender = SoloTodoUser().get_bot().email_recipient_text()
                translation.activate(email_language)

                email_recipients = [user.email_recipient_text()]

                html_message = render_to_string(
                    'mailing/entity_subscription_pricing_changed.html', {
                        'entity_subscription': self,
                        'user': user,
                        'timestamp': timezone.now(),
                        'host': settings.BACKEND_HOST,
                        'old_is_available': old_is_available,
                        'old_normal_price': old_history and
                        old_history.normal_price,
                        'old_offer_price': old_history and
                        old_history.offer_price,
                        'new_is_available': new_is_available,
                        'new_normal_price': new_history and
                        new_history.normal_price,
                        'new_offer_price': new_history and
                        new_history.offer_price,
                    })

                send_mail('{}: {} - {}'.format(
                    _('Pricing change'), self.entity.store, self.entity.name),
                          'Price change', sender, email_recipients,
                          html_message=html_message)

        self.last_history_seen = new_history
        self.save()

    class Meta:
        ordering = ('entity', )
