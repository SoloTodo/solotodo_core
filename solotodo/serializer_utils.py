from rest_framework import serializers

from solotodo.models import Store, Product


class UserFilteredPrimaryKeyRelatedField(serializers.PrimaryKeyRelatedField):
    permission = 'view'
    klass = None

    def get_queryset(self):
        request = self.context['request']
        return self.klass.objects.filter_by_user_perms(
            request.user, self.permission)


class StorePrimaryKeyRelatedField(UserFilteredPrimaryKeyRelatedField):
    permission = 'view_store'
    klass = Store


class ProductPrimaryKeyRelatedField(UserFilteredPrimaryKeyRelatedField):
    permission = 'view_product'
    klass = Product
