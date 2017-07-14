from django.contrib import admin

# Register your models here.
from solotodo.models import Currency, Entity, EntityHistory, ProductType, \
    SoloTodoUser, Store, Country, Product, StoreUpdateLog

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
    readonly_fields = ['creator']

admin.site.register(Product, ProductModelAdmin)
admin.site.register(ProductType)
admin.site.register(SoloTodoUser)
admin.site.register(Store)
admin.site.register(StoreUpdateLog)
