from django.contrib import admin

from hardware.models import Budget, BudgetEntry


@admin.register(Budget)
class BudgetModelAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'user', 'creation_date']
    readonly_fields = ['user', 'products_pool']


admin.site.register(BudgetEntry)
