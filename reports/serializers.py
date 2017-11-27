from rest_framework import serializers

from reports.models import Report


class ReportSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Report
        fields = ('url', 'id', 'name', 'slug')
