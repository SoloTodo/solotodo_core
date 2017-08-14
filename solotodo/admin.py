from custom_user.admin import EmailUserAdmin
from django.contrib import admin

# Register your models here.
from guardian.admin import GuardedModelAdmin

from solotodo.models import Currency, Entity, EntityHistory, ProductType, \
    SoloTodoUser, Store, Country, Product, StoreUpdateLog, Language, \
    StoreType, ProductTypeTier

admin.site.register(Language)
admin.site.register(Country)
admin.site.register(Currency)


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
admin.site.register(SoloTodoUser, EmailUserAdmin)
admin.site.register(StoreType)
admin.site.register(Store, GuardedModelAdmin)
admin.site.register(StoreUpdateLog)
