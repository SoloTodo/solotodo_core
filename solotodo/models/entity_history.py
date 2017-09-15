from django.db import models

from solotodo.models.entity import Entity


class EntityHistoryQueryset(models.QuerySet):
    def get_available(self):
        return self.exclude(stock=0)


class EntityHistory(models.Model):
    entity = models.ForeignKey(Entity)
    timestamp = models.DateTimeField()
    stock = models.IntegerField(db_index=True)
    normal_price = models.DecimalField(decimal_places=2, max_digits=12)
    offer_price = models.DecimalField(decimal_places=2, max_digits=12)
    cell_monthly_payment = models.DecimalField(decimal_places=2, max_digits=12,
                                               null=True, blank=True)
    objects = EntityHistoryQueryset.as_manager()

    def __str__(self):
        return u'{} - {}'.format(self.entity, self.timestamp)

    def is_available(self):
        return self.stock != 0

    class Meta:
        app_label = 'solotodo'
        ordering = ['entity', 'timestamp']
