from django.contrib import admin
from guardian.admin import GuardedModelAdmin

from reports.models import Report

admin.site.register(Report, GuardedModelAdmin)
