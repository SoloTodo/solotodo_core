from django.db import models


class NumberFormat(models.Model):
    name = models.CharField(max_length=10)
    thousands_separator = models.CharField(max_length=3)
    decimal_separator = models.CharField(max_length=3)

    def __str__(self):
        return self.name

    class Meta:
        app_label = 'solotodo'
        ordering = ('name', )
