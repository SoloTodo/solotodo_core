from guardian.shortcuts import get_objects_for_user
from rest_framework import viewsets

from reports.models import Report
from reports.serializers import ReportSerializer


class ReportViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Report.objects.all()
    serializer_class = ReportSerializer

    def get_queryset(self):
        return get_objects_for_user(self.request.user, 'view_report', Report)
