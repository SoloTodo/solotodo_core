from django.contrib import admin

from alerts.models import Alert, AlertNotification


@admin.register(Alert)
class AlertModelAdmin(admin.ModelAdmin):
    list_display = ('id', 'product', 'email', 'creation_date', 'last_updated')
    readonly_fields = ('product', 'normal_price_registry',
                       'offer_price_registry')


@admin.register(AlertNotification)
class AlertNotificationModelAdmin(admin.ModelAdmin):
    list_display = ('id', 'alert_product', 'alert_email', 'creation_date')
    readonly_fields = ('previous_normal_price_registry',
                       'previous_offer_price_registry')

    def alert_product(self, obj):
        return obj.alert.product

    def alert_email(self, obj):
        return obj.alert.email
