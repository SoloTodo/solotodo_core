from guardian.shortcuts import get_objects_for_user
from rest_framework import viewsets, status
from rest_framework.decorators import list_route
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework_tracking.mixins import LoggingMixin

from reports.forms.report_current_prices_form import ReportCurrentPricesForm
from reports.forms.report_prices_history_form import ReportPricesHistoryForm
from reports.forms.report_store_analysis_form import ReportStoreAnalysisForm
from reports.forms.report_websites_traffic_form import \
    ReportWebsitesTrafficForm
from reports.forms.report_weekly_prices_form import ReportWeeklyPricesForm
from reports.models import Report, ReportDownload
from reports.serializers import ReportSerializer
from solotodo_core.s3utils import PrivateS3Boto3Storage


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

        report_path = form.generate_report()['path']

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

    @list_route()
    def store_analysis(self, request):
        report = Report.objects.get(slug='store_analysis')
        user = request.user

        if not user.has_perm('view_report', report):
            raise PermissionDenied

        form = ReportStoreAnalysisForm(request.user, request.GET)

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

    @list_route()
    def weekly_prices(self, request):
        report = Report.objects.get(slug='weekly_prices')
        user = request.user

        if not user.has_perm('view_report', report):
            raise PermissionDenied

        form = ReportWeeklyPricesForm(request.user, request.GET)

        if not form.is_valid():
            return Response({
                'errors': form.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        report_path = form.generate_report()['path']

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

    @list_route()
    def prices_history(self, request):
        report = Report.objects.get(slug='prices_history')
        user = request.user

        if not user.has_perm('view_report', report):
            raise PermissionDenied

        form = ReportPricesHistoryForm(request.user, request.GET)

        if not form.is_valid():
            return Response({
                'errors': form.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        report_path = form.generate_report()['path']

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

    @list_route()
    def websites_traffic(self, request):
        report = Report.objects.get(slug='websites_traffic')
        user = request.user

        if not user.has_perm('view_report', report):
            raise PermissionDenied

        form = ReportWebsitesTrafficForm(request.user, request.GET)

        if not form.is_valid():
            return Response({
                'errors': form.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        report_path = form.generate_report()['path']

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
