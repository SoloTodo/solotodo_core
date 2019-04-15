from django.db import models

from .entity_position_section import EntityPositionSection
from solotodo.models import EntityHistory, Store, Category


class EntityPositionQuerySet(models.QuerySet):
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
            entity_history__entity__store__in=stores_with_permissions,
            entity_history__entity__category__in=categories_with_permissions)


class EntityPosition(models.Model):
    value = models.IntegerField()
    entity_history = models.ForeignKey(EntityHistory, on_delete=models.CASCADE)
    section = models.ForeignKey(EntityPositionSection,
                                on_delete=models.CASCADE)

    objects = EntityPositionQuerySet.as_manager()

    def __str__(self):
        return '{} - {} - {}'.format(self.value, self.entity_history,
                                     self.section)

    class Meta:
        app_label = 'entity_positions'
        ordering = ('entity_history', 'section', 'value')
