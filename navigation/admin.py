from django.contrib import admin

from navigation.models import NavDepartment, NavSection, NavItem


@admin.register(NavDepartment)
class NavDepartmentModelAdmin(admin.ModelAdmin):
    list_display = ['name', 'country', 'ordering']
    list_filter = ['country']


@admin.register(NavSection)
class NavSectionModelAdmin(admin.ModelAdmin):
    def department_country(self, obj):
        return obj.department.country

    def department_name(self, obj):
        return obj.department.name

    list_display = ['name', 'department_name', 'path', 'department_country',
                    'ordering']
    list_filter = ['department__country']


@admin.register(NavItem)
class NavItemModelAdmin(admin.ModelAdmin):
    def section_name(self, obj):
        return obj.section.name

    def department_name(self, obj):
        return obj.section.department.name

    def department_country(self, obj):
        return obj.section.department.country

    list_display = ['name', 'section_name', 'department_name', 'path',
                    'department_country', 'ordering']
    list_filter = ['section__department__country']
