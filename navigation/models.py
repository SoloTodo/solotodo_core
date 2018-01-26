from django.db import models

from solotodo.models import Country


class NavDepartment(models.Model):
    country = models.ForeignKey(Country, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    ordering = models.IntegerField()

    def __str__(self):
        return '{} - {}'.format(self.country, self.name)

    class Meta:
        ordering = ['country', 'ordering']


class NavSection(models.Model):
    department = models.ForeignKey(NavDepartment, on_delete=models.CASCADE,
                                   related_name='sections')
    name = models.CharField(max_length=100)
    path = models.CharField(max_length=255)
    ordering = models.IntegerField()

    def __str__(self):
        return '{} - {}'.format(self.department, self.name)

    class Meta:
        ordering = ['department', 'ordering']


class NavItem(models.Model):
    section = models.ForeignKey(NavSection, on_delete=models.CASCADE,
                                related_name='items')
    name = models.CharField(max_length=100)
    path = models.CharField(max_length=255)
    ordering = models.IntegerField()

    def __str__(self):
        return '{} - {}'.format(self.section, self.name)

    class Meta:
        ordering = ['section', 'ordering']
