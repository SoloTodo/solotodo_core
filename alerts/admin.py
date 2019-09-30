from django.contrib import admin

from .models import ProductPriceAlert, ProductPriceAlertHistory


@admin.register(ProductPriceAlert)
class ProductPriceAlertAdmin(admin.ModelAdmin):
    list_display = ('id', 'product', 'user', 'email',
                    'active_history', 'creation_date')
    readonly_fields = ('product', 'user')


@admin.register(ProductPriceAlertHistory)
class ProductPriceAlertHistoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'alert', 'timestamp')
    readonly_fields = ('alert', 'entries')
