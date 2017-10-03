from django.contrib.auth import get_user_model
from django.db import models

from solotodo.models import ApiClient
from .entity_history import EntityHistory


class LeadQuerySet(models.QuerySet):
    def filter_by_user_perms(self, user, permission):
        from .category import Category
        from .store import Store

        synth_permissions = {
            'view_lead': {
                'store': 'view_store_leads',
                'category': 'view_category_leads',
                'api_client': 'view_api_client_leads'
            }
        }

        assert permission in synth_permissions

        permissions = synth_permissions[permission]

        stores_with_permissions = Store.objects.filter_by_user_perms(
            user, permissions['store'])
        categories_with_permissions = Category.objects.filter_by_user_perms(
            user, permissions['category'])
        api_clients_with_permissions = ApiClient.objects.filter_by_user_perms(
            user, permissions['api_client'])

        return self.filter(
            entity_history__entity__store__in=stores_with_permissions,
            entity_history__entity__category__in=categories_with_permissions,
            api_client__in=api_clients_with_permissions,
        )


class Lead(models.Model):
    entity_history = models.ForeignKey(EntityHistory)
    timestamp = models.DateTimeField()
    user = models.ForeignKey(get_user_model())
    ip = models.GenericIPAddressField()
    api_client = models.ForeignKey(ApiClient)

    objects = LeadQuerySet.as_manager()

    def __str__(self):
        return '{} - {}'.format(self.entity_history.entity, self.timestamp)

    class Meta:
        app_label = 'solotodo'
        ordering = ('entity_history', 'timestamp')
        permissions = (
            ('view_leads_user_data',
             'Can view the IP and user associated to all leads'),
            ('backend_list_leads', 'Can view list of leads in the backend'),
        )
