from django.contrib import admin
from soicos_conversions.models import SoicosConversion


@admin.register(SoicosConversion)
class SoicosConversionAdmin(admin.ModelAdmin):
    list_display = ['lead', 'creation_date', 'validation_date', 'ip',
                    'transaction_id', 'payout', 'transaction_total', 'status']

    readonly_fields = ['lead']
