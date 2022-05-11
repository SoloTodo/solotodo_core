from guardian.shortcuts import get_objects_for_user
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from reports.forms.pc_factory_sku_analysis_form import PcFactorySkuAnalysisForm
from reports.forms.report_current_prices_form import ReportCurrentPricesForm
from reports.forms.report_daily_prices_form import ReportDailyPricesForm
from reports.forms.report_prices_history_form import ReportPricesHistoryForm
from reports.forms.report_sec_prices_form import ReportSecPricesForm
from reports.forms.report_store_analysis_form import ReportStoreAnalysisForm
from reports.forms.report_websites_traffic_form import \
    ReportWebsitesTrafficForm
from reports.forms.report_weekly_prices_form import ReportWeeklyPricesForm
from reports.forms.report_wtb_form import ReportWtbForm
from reports.forms.report_soicos_conversions import ReportSoicosConversions
from reports.forms.report_wtb_prices_form import ReportWtbPricesForm
from reports.models import Report, ReportDownload
from reports.serializers import ReportSerializer
from reports.tasks import send_daily_prices_task, send_current_prices_task, \
    send_store_analysis_report_task
from solotodo_core.s3utils import PrivateS3Boto3Storage


class ReportViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Report.objects.all()
    serializer_class = ReportSerializer

    def get_queryset(self):
        return get_objects_for_user(self.request.user, 'view_report', Report)

    @action(detail=False)
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

        send_current_prices_task.delay([user.id], request.META['QUERY_STRING'])

        return Response({
            'message': 'ok'
        }, status=status.HTTP_200_OK)

    @action(detail=False)
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

        send_store_analysis_report_task.delay(
            user.id, request.META['QUERY_STRING'])

        return Response({
            'message': 'ok'
        }, status=status.HTTP_200_OK)

    @action(detail=False)
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

    @action(detail=False)
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

    @action(detail=False)
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

    @action(detail=False)
    def sec_prices(self, request):
        report = Report.objects.get(slug='sec_prices')
        user = request.user

        if not user.has_perm('view_report', report):
            raise PermissionDenied

        form = ReportSecPricesForm(request.user, request.GET)

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

    @action(detail=False)
    def daily_prices(self, request):
        report = Report.objects.get(slug='daily_prices')
        user = request.user

        if not user.has_perm('view_report', report):
            raise PermissionDenied

        form = ReportDailyPricesForm(request.user, request.GET)

        if not form.is_valid():
            return Response({
                'errors': form.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        send_daily_prices_task.delay(user.id, request.META['QUERY_STRING'])

        return Response({
            'message': 'ok'
        }, status=status.HTTP_200_OK)

    @action(detail=False)
    def wtb_report(self, request):
        report = Report.objects.get(slug='wtb_report')
        user = request.user

        if not user.has_perm('view_report', report):
            raise PermissionDenied

        form = ReportWtbForm(request.user, request.GET)

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

    @action(detail=False)
    def wtb_prices_report(self, request):
        report = Report.objects.get(slug='wtb_prices_report')
        user = request.user

        if not user.has_perm('view_report', report):
            raise PermissionDenied

        form = ReportWtbPricesForm(request.user, request.GET)

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

    @action(detail=False)
    def soicos_conversions(self, request):
        report = Report.objects.get(slug='soicos_conversions')
        user = request.user

        if not user.has_perm('view_report', report):
            raise PermissionDenied

        form = ReportSoicosConversions(request.user, request.GET)

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

    @action(detail=False)
    def pc_factory_sku_analysis(self, request):
        report = Report.objects.get(slug='pc_factory_sku_analysis')
        user = request.user

        if not user.has_perm('view_report', report):
            raise PermissionDenied

        data = PcFactorySkuAnalysisForm.generate_report()

        return Response(data)
