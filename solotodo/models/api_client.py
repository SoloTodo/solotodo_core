from django.db import models
from guardian.shortcuts import get_objects_for_user


class ApiClientQuerySet(models.QuerySet):
    def filter_by_user_perms(self, user, permission):
        return get_objects_for_user(user, permission, self)


class ApiClient(models.Model):
    name = models.CharField(max_length=100)
    url = models.URLField()

    objects = ApiClientQuerySet.as_manager()

    def __str__(self):
        return self.name

    class Meta:
        app_label = 'solotodo'
        ordering = ('name', )
        permissions = [
            ('view_api_client', 'Can view the API client'),
            ('view_api_client_leads',
             'Can view the leads associated to this API client')
        ]
