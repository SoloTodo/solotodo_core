from custom_user.admin import EmailUserAdmin
from django.contrib import admin

# Register your models here.
from guardian.admin import GuardedModelAdmin

from solotodo.models import Currency, Entity, EntityHistory, ProductType, \
    SoloTodoUser, Store, Country, Product, StoreUpdateLog, Language, \
    StoreType, ProductTypeTier, NumberFormat

admin.site.register(Language)
admin.site.register(Country)
admin.site.register(Currency)
admin.site.register(NumberFormat)


class EntityModelAdmin(admin.ModelAdmin):
    readonly_fields = ['store', 'product_type', 'scraped_product_type',
                       'currency', 'product', 'cell_plan', 'active_registry',
                       'latest_association_user']

admin.site.register(Entity, EntityModelAdmin)


class EntityHistoryModelAdmin(admin.ModelAdmin):
    readonly_fields = ['entity']

admin.site.register(EntityHistory, EntityHistoryModelAdmin)


class ProductModelAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'product_type']
    readonly_fields = ['creator', 'instance_model']

admin.site.register(Product, ProductModelAdmin)
admin.site.register(ProductTypeTier)
admin.site.register(ProductType, GuardedModelAdmin)


class SoloTodoUserAdmin(EmailUserAdmin):
    fieldsets = EmailUserAdmin.fieldsets + \
                (('Additional information', {'fields': (
                    'preferred_language',
                    'preferred_currency',
                    'preferred_country',
                    'preferred_number_format')}),
                 )

admin.site.register(SoloTodoUser, SoloTodoUserAdmin)
admin.site.register(StoreType)
admin.site.register(Store, GuardedModelAdmin)
admin.site.register(StoreUpdateLog)
