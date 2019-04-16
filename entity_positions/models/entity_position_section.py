from django.db import models

from solotodo.models import Store, Category


class EntityPositionSectionQuerySet(models.QuerySet):
    def filter_by_user_perms(self, user, permission):
        synth_permissions = {
            'view_entity_positions': {
                'store': 'view_store_entity_positions',
                'category': 'view_category_entity_positions'
            }
        }

        assert permission in synth_permissions

        permission = synth_permissions[permission]

        stores_with_permissions = Store.objects.filter_by_user_perms(
            user, permission['store'])
        categories_with_permissions = Category.objects.filter_by_user_perms(
            user, permission['category'])

        return self.filter(
            store__in=stores_with_permissions,
            entityposition__entity_history__entity__category__in=categories_with_permissions)


class EntityPositionSection(models.Model):
    name = models.CharField(max_length=512)
    store = models.ForeignKey(Store, on_delete=models.CASCADE)

    objects = EntityPositionSectionQuerySet.as_manager()

    def __str__(self):
        return '{} - {}'.format(self.store, self.name)

    class Meta:
        app_label = 'entity_positions'
        ordering = ('store', 'name')
