from django.db import models
from guardian.shortcuts import get_objects_for_user


class WebsiteQuerySet(models.QuerySet):
    def filter_by_user_perms(self, user, permission):
        return get_objects_for_user(user, permission, self)


class Website(models.Model):
    name = models.CharField(max_length=100)
    url = models.URLField()

    objects = WebsiteQuerySet.as_manager()

    def __str__(self):
        return self.name

    class Meta:
        app_label = 'solotodo'
        ordering = ('name', )
        permissions = [
            ('view_website_visits',
             'Can view the visits associated to this website'),
            ('view_website_leads',
             'Can view the leads associated to this website'),
        ]
