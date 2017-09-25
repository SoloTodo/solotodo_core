from django.contrib.auth.models import Permission
from django.utils.translation import gettext_lazy as _
from custom_user.admin import EmailUserAdmin
from django.contrib import admin

# Register your models here.
from guardian.admin import GuardedModelAdmin

from solotodo.models import Currency, Entity, EntityHistory, Category, \
    SoloTodoUser, Store, Country, Product, StoreUpdateLog, Language, \
    StoreType, CategoryTier, NumberFormat, EntityLog, EntityState, ApiClient


class PermissionModelAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'codename']


admin.site.register(Permission, PermissionModelAdmin)


class ApiClientModelAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'url']


admin.site.register(ApiClient, ApiClientModelAdmin)
admin.site.register(Language)
admin.site.register(Country)
admin.site.register(Currency)
admin.site.register(NumberFormat)
admin.site.register(EntityState)


class EntityModelAdmin(admin.ModelAdmin):
    readonly_fields = ['store', 'category', 'scraped_category',
                       'currency', 'product', 'cell_plan', 'active_registry',
                       'last_association_user', 'last_staff_change_user',
                       'last_staff_access_user', 'last_pricing_update_user']


admin.site.register(Entity, EntityModelAdmin)


class EntityLogModelAdmin(admin.ModelAdmin):
    readonly_fields = ['entity', 'category', 'scraped_category',
                       'currency', 'product', 'cell_plan', 'user']

    def get_queryset(self, request):
        return EntityLog.objects.select_related()


admin.site.register(EntityLog, EntityLogModelAdmin)


class EntityHistoryModelAdmin(admin.ModelAdmin):
    readonly_fields = ['entity']


admin.site.register(EntityHistory, EntityHistoryModelAdmin)


class ProductCreatorListFilter(admin.SimpleListFilter):
    title = _('Creator')
    parameter_name = 'creator'

    def lookups(self, request, model_admin):
        return [(u.id, u.email)
                for u in SoloTodoUser.objects.filter(is_staff=True)]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(creator=self.value())


class ProductModelAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'category', 'creator', 'creation_date',
                    'last_updated']
    list_filter = ['instance_model__model__category', ProductCreatorListFilter]
    readonly_fields = ['creator', 'instance_model']

    def get_queryset(self, request):
        return Product.objects.select_related()


admin.site.register(Product, ProductModelAdmin)
admin.site.register(CategoryTier)
admin.site.register(Category, GuardedModelAdmin)


class SoloTodoUserAdmin(EmailUserAdmin):
    fieldsets = EmailUserAdmin.fieldsets + \
                (('Additional information', {'fields': (
                    'first_name',
                    'last_name',
                    'preferred_language',
                    'preferred_currency',
                    'preferred_country',
                    'preferred_number_format',
                    'preferred_store')}),
                 )


admin.site.register(SoloTodoUser, SoloTodoUserAdmin)
admin.site.register(StoreType)


class StoreModelAdmin(GuardedModelAdmin):
    list_display = ['__str__', 'type', 'country']
    list_filter = ['type', 'country']


admin.site.register(Store, StoreModelAdmin)
admin.site.register(StoreUpdateLog)
