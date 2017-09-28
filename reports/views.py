from guardian.shortcuts import get_objects_for_user
from rest_framework import viewsets
from rest_framework.decorators import list_route
from rest_framework.response import Response

from reports.models import Report
from reports.serializers import ReportSerializer


class ReportViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Report.objects.all()
    serializer_class = ReportSerializer

    def get_queryset(self):
        return get_objects_for_user(self.request.user, 'view_report', Report)

    @list_route()
    def current_prices(self, request):
        report = Report.objects.get(pk=1)
        report_url = report.render_current_prices(request.user)
        return Response({
            'url': report_url
        })
