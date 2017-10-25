from django.contrib import admin

from entity_subscriptions.models import EntitySubscription


@admin.register(EntitySubscription)
class EntitySubscriptionModelAdmin(admin.ModelAdmin):
    readonly_fields = ['entity', 'last_history_seen', 'users']
