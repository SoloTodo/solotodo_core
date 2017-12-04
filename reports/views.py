from django.conf import settings
from guardian.shortcuts import get_objects_for_user
from rest_framework import viewsets, status
from rest_framework.decorators import list_route
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework_tracking.mixins import LoggingMixin

from reports.forms.report_current_prices_form import ReportCurrentPricesForm
from reports.models import Report, ReportDownload
from reports.serializers import ReportSerializer
from solotodo_try.s3utils import PrivateS3Boto3Storage


class ReportViewSet(LoggingMixin, viewsets.ReadOnlyModelViewSet):
    queryset = Report.objects.all()
    serializer_class = ReportSerializer

    def get_queryset(self):
        return get_objects_for_user(self.request.user, 'view_report', Report)

    @list_route()
    def current_prices(self, request):
        report = Report.objects.get(slug='current_prices')
        user = request.user

        if not user.has_perm('view_report', report):
            raise PermissionDenied

        form = ReportCurrentPricesForm(request.user, request.GET)

        if not form.is_valid():
            return Response({
                'errors': form.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        report_path = form.generate_report()

        ReportDownload.objects.create(
            report=report,
            user=user,
            file=report_path
        )

        storage = PrivateS3Boto3Storage()
        report_url = storage.url(report_path)
        return Response({
            'url': report_url
        })
