from django.contrib.auth.models import Permission
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from custom_user.admin import EmailUserAdmin
from django.contrib import admin

# Register your models here.
from guardian.admin import GuardedModelAdmin

from solotodo.models import Currency, Entity, EntityHistory, Category, \
    SoloTodoUser, Store, Country, Product, StoreUpdateLog, Language, \
    StoreType, CategoryTier, NumberFormat, EntityLog, Website, \
    CategorySpecsFilter, CategorySpecsOrder, Lead, Visit, Rating, \
    ProductPicture


@admin.register(Permission)
class PermissionModelAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'codename']


@admin.register(Website)
class WebsiteModelAdmin(GuardedModelAdmin):
    list_display = ['__str__', 'url']


admin.site.register(Language)
admin.site.register(Country)
admin.site.register(Currency)
admin.site.register(NumberFormat)


@admin.register(Entity)
class EntityModelAdmin(admin.ModelAdmin):
    readonly_fields = ['store', 'category', 'scraped_category',
                       'currency', 'product', 'cell_plan', 'active_registry',
                       'last_association_user', 'last_staff_access_user', ]


@admin.register(EntityLog)
class EntityLogModelAdmin(admin.ModelAdmin):
    readonly_fields = ['entity', 'category', 'scraped_category',
                       'currency', 'product', 'cell_plan', 'user']

    def get_queryset(self, request):
        return EntityLog.objects.select_related()


@admin.register(EntityHistory)
class EntityHistoryModelAdmin(admin.ModelAdmin):
    readonly_fields = ['entity']


class ProductCreatorListFilter(admin.SimpleListFilter):
    title = _('Creator')
    parameter_name = 'creator'

    def lookups(self, request, model_admin):
        return [(u.id, u.email)
                for u in SoloTodoUser.objects.filter(is_staff=True)]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(creator=self.value())


@admin.register(Product)
class ProductModelAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'category', 'creator', 'creation_date',
                    'last_updated']
    list_filter = ['instance_model__model__category', ProductCreatorListFilter]
    readonly_fields = ['creator', 'instance_model']

    def get_queryset(self, request):
        return Product.objects.select_related()


@admin.register(ProductPicture)
class ProductPictureModelAdmin(admin.ModelAdmin):
    list_display = ['id', 'product', 'file', 'ordering']
    list_filter = ['product__instance_model__model__category']
    raw_id_fields = ('product',)


admin.site.register(CategoryTier)
admin.site.register(Category, GuardedModelAdmin)


@admin.register(CategorySpecsFilter)
class CategorySpecsFilterModelAdmin(admin.ModelAdmin):
    def meta_model_link(self, obj):
        return mark_safe('<a href="/metamodel/models/{}">{}</a>'.format(
            obj.meta_model_id, obj.meta_model))

    list_filter = ('category', )
    list_display = ('category', 'name', 'meta_model_link', 'type', 'es_field',
                    'value_field')


@admin.register(CategorySpecsOrder)
class CategorySpecsOrderModelAdmin(admin.ModelAdmin):
    list_filter = ('category', )
    list_display = ('category', 'name', 'es_field')


@admin.register(SoloTodoUser)
class SoloTodoUserAdmin(EmailUserAdmin):
    fieldsets = EmailUserAdmin.fieldsets + \
                (('Additional information', {'fields': (
                    'first_name',
                    'last_name',
                    'preferred_language',
                    'preferred_currency',
                    'preferred_country',
                    'preferred_number_format',
                    'preferred_store',
                    'preferred_stores',
                    'preferred_stores_last_updated',
                )}),
                 )


admin.site.register(StoreType)


@admin.register(Store)
class StoreModelAdmin(GuardedModelAdmin):
    list_display = ['__str__', 'type', 'country']
    list_filter = ['type', 'country']


admin.site.register(StoreUpdateLog)


@admin.register(Lead)
class LeadModelAdmin(admin.ModelAdmin):
    list_display = ['product_link', 'store_link', 'website', 'timestamp', 'ip',
                    'user']
    list_filter = ['website', 'entity_history__entity__category',
                   'entity_history__entity__store']
    readonly_fields = ['website', 'entity_history', 'user', 'ip', 'timestamp']

    def get_queryset(self, request):
        return Lead.objects.select_related(
            'entity_history__entity__store',
            'website',
            'entity_history__entity__product__instance_model',
            'user'
        )

    def product_link(self, obj):
        website_url = '{}/products/{}'.format(
            obj.website.url, obj.entity_history.entity.product_id)

        return format_html("<a href='{url}'>{product}</a>",
                           url=website_url,
                           product=str(obj.entity_history.entity.product))

    product_link.short_description = 'Product'

    def store_link(self, obj):
        from django.conf import settings
        backend_link = '{}entities/{}'.format(
            settings.BACKEND_HOST, obj.entity_history.entity.id)

        return format_html("<a href='{url}'>{store}</a>", url=backend_link,
                           store=str(obj.entity_history.entity.store))

    store_link.short_description = 'Store'


@admin.register(Visit)
class VisitModelAdmin(admin.ModelAdmin):
    list_display = ['product_link', 'website_link', 'timestamp', 'ip', 'user']
    list_filter = ['website', 'product__instance_model__model__category']
    readonly_fields = ['product', 'website', 'timestamp', 'ip', 'user']

    def product_link(self, obj):
        from django.conf import settings
        backend_link = '{}products/{}'.format(settings.BACKEND_HOST,
                                              obj.product_id)

        return format_html("<a href='{url}'>{product}</a>",
                           url=backend_link, product=str(obj.product))

    product_link.short_description = 'Product'

    def website_link(self, obj):
        website_url = '{}/products/{}'.format(obj.website.url, obj.product_id)

        return format_html("<a href='{url}'>{product}</a>",
                           url=website_url, product=str(obj.website))

    website_link.short_description = 'Website'

    def get_queryset(self, request):
        return Visit.objects.select_related(
            'product__instance_model__model__category',
            'website',
            'user'
        )


@admin.register(Rating)
class RatingModelAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'product', 'store', 'creation_date',
                    'approval_date')
    list_filter = ('store', )
    readonly_fields = ('product', 'store', 'user')
