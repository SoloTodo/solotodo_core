from django.contrib.auth import get_user_model
from django.db import models

from solotodo.models import Website
from .entity_history import EntityHistory


class LeadQuerySet(models.QuerySet):
    def filter_by_user_perms(self, user, permission):
        from .category import Category
        from .store import Store

        synth_permissions = {
            'view_lead': {
                'store': 'view_store_leads',
                'category': 'view_category_leads',
                'website': 'view_website_leads'
            }
        }

        assert permission in synth_permissions

        permissions = synth_permissions[permission]

        stores_with_permissions = Store.objects.filter_by_user_perms(
            user, permissions['store'])
        categories_with_permissions = Category.objects.filter_by_user_perms(
            user, permissions['category'])
        websites_with_permissions = Website.objects.filter_by_user_perms(
            user, permissions['website'])

        return self.filter(
            entity_history__entity__store__in=stores_with_permissions,
            entity_history__entity__category__in=categories_with_permissions,
            website__in=websites_with_permissions,
        )


class Lead(models.Model):
    entity_history = models.ForeignKey(EntityHistory, on_delete=models.CASCADE)
    timestamp = models.DateTimeField()
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    ip = models.GenericIPAddressField()
    website = models.ForeignKey(Website, on_delete=models.CASCADE)

    objects = LeadQuerySet.as_manager()

    def __str__(self):
        return '{} - {}'.format(self.entity_history.entity, self.timestamp)

    class Meta:
        app_label = 'solotodo'
        ordering = ('-timestamp', )
        permissions = (
            ('view_leads_user_data',
             'Can view the IP and user associated to all leads'),
            ('backend_list_leads', 'Can view list of leads in the backend'),
        )
