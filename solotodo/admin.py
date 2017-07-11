from django.contrib import admin

# Register your models here.
from solotodo.models import Currency, Entity, EntityHistory, ProductType, \
    SoloTodoUser, Store

admin.site.register(Currency)
admin.site.register(Entity)
admin.site.register(EntityHistory)
admin.site.register(ProductType)
admin.site.register(SoloTodoUser)
admin.site.register(Store)

