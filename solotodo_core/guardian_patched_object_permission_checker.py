from itertools import chain

from django.contrib.auth.models import Permission
from guardian.core import ObjectPermissionChecker
from guardian.ctypes import get_content_type


class GuardianPatchedObjectPermissionChecker(ObjectPermissionChecker):
    """
    Changes the default behaviour of guardian permissions so that a permission
    applied to a content type also applies to all the individual objects of
    that type
    """

    def get_user_perms(self, obj):
        perms = super(GuardianPatchedObjectPermissionChecker, self).get_user_perms(obj)
        ctype = get_content_type(obj)
        global_perms_qs = self.user.user_permissions.filter(content_type=ctype)
        global_perms = global_perms_qs.values_list('codename', flat=True)
        return list(set(chain(perms, global_perms)))

    def get_group_perms(self, obj):
        perms = super(GuardianPatchedObjectPermissionChecker, self).get_group_perms(obj)
        ctype = get_content_type(obj)
        global_perms_qs = Permission.objects.filter(
            group__user=self.user, content_type=ctype)
        global_perms = global_perms_qs.values_list('codename', flat=True)
        return list(set(chain(perms, global_perms)))
