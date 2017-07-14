from django.db import models

from solotodo.models.entity import Entity


class EntityHistory(models.Model):
    entity = models.ForeignKey(Entity)
    date = models.DateField(db_index=True)
    stock = models.IntegerField(db_index=True)
    normal_price = models.DecimalField(decimal_places=2, max_digits=12)
    offer_price = models.DecimalField(decimal_places=2, max_digits=12)
    cell_monthly_payment = models.DecimalField(decimal_places=2, max_digits=12,
                                               null=True, blank=True)

    def __str__(self):
        return u'{} - {}'.format(self.entity, self.date)

    class Meta:
        app_label = 'solotodo'
        ordering = ['entity', 'date']
        unique_together = ('entity', 'date')
