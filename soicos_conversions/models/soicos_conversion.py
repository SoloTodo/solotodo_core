from django.db import models
from solotodo.models import Lead


class SoicosConversion(models.Model):
    STATUS_CHOICES = (
        (1, 'OK'),
        (2, 'Canceled'),
        (3, 'Pending'),
        (4, 'Blocked'),
        (5, 'Invalid country'))

    lead = models.ForeignKey(Lead, on_delete=models.CASCADE)
    creation_date = models.DateTimeField()
    validation_date = models.DateTimeField(blank=True, null=True)
    ip = models.GenericIPAddressField()
    transaction_id = models.CharField(max_length=256)
    payout = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_total = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.IntegerField(choices=STATUS_CHOICES)

    def __str__(self):
        return '{} - {}'.format(self.lead, self.creation_date)

    class Meta:
        app_label = 'soicos_conversions'
