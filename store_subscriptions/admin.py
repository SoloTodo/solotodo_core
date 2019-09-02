from django.contrib import admin
from .models import StoreSubscription

from solotodo.serializers import CategorySerializer


@admin.register(StoreSubscription)
class StoreSubscriptionAdmin(admin.ModelAdmin):
    categories = CategorySerializer(many=True)

    list_display = ('id', 'user', 'store', 'categories', 'creation_date')
    readonly_fields = ('user',)
