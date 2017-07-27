from django.db import models
from django.utils.translation import ugettext_lazy as _
from custom_user.models import AbstractEmailUser

from .country import Country
from .currency import Currency
from .language import Language


class SoloTodoUser(AbstractEmailUser):
    first_name = models.CharField(_('first name'), max_length=30, blank=True,
                                  null=True)
    last_name = models.CharField(_('last name'), max_length=30, blank=True,
                                 null=True)
    preferred_language = models.ForeignKey(Language, blank=True, null=True)
    preferred_currency = models.ForeignKey(Currency, blank=True, null=True)
    preferred_country = models.ForeignKey(Country, blank=True,
                                          null=True)
    permissions = property(lambda self: sorted(self.get_all_permissions()))

    class Meta:
        app_label = 'solotodo'
        verbose_name = 'SoloTodo User'
        verbose_name_plural = 'SoloTodo Users'
