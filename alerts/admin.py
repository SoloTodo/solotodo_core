from django.contrib import admin

from .models import Alert
from .models import AnonymousAlert
from .models import AlertNotification


@admin.register(Alert)
class AlertModelAdmin(admin.ModelAdmin):
    list_display = ('id', 'product', 'creation_date', 'last_updated')
    readonly_fields = ('product', 'normal_price_registry',
                       'offer_price_registry')


@admin.register(AlertNotification)
class AlertNotificationModelAdmin(admin.ModelAdmin):
    list_display = ('id', 'alert_product', 'creation_date')
    readonly_fields = ('alert', 'previous_normal_price_registry',
                       'previous_offer_price_registry')

    def alert_product(self, obj):
        return obj.alert.product


@admin.register(AnonymousAlert)
class AnonymousAlertModelAdmin(admin.ModelAdmin):
    list_display = ('id', 'email', 'alert_product', 'alert_creation_date',
                    'alert_last_updated')
    readonly_fields = ('alert',)

    def alert_product(self, obj):
        return obj.alert.product

    def alert_creation_date(self, obj):
        return obj.alert.creation_date

    def alert_last_updated(self, obj):
        return obj.alert.last_updated
