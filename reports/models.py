from django.contrib.auth import get_user_model
from django.db import models

from solotodo.models import Entity, Product
from solotodo_try.s3utils import PrivateS3Boto3Storage


class Report(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField()

    def __str__(self):
        return self.name

    class Meta:
        ordering = ('name',)
        permissions = (
            ('view_report', 'Can view the report'),
            ('backend_list_reports', 'Can view report list in backend'),
        )


class ReportDownload(models.Model):
    report = models.ForeignKey(Report, on_delete=models.CASCADE)
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    file = models.FileField(storage=PrivateS3Boto3Storage())
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return '{} - {} - {}'.format(self.report, self.user, self.timestamp)

    class Meta:
        ordering = ('-timestamp', )
