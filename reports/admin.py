from django.contrib import admin
from guardian.admin import GuardedModelAdmin

from reports.models import Report, ReportDownload


@admin.register(Report)
class ReportModelAdmin(GuardedModelAdmin):
    list_display = ('name', 'slug')


@admin.register(ReportDownload)
class ReportDownloadModelAdmin(admin.ModelAdmin):
    readonly_fields = ('user', )
