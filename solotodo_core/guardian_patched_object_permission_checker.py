from guardian.core import ObjectPermissionChecker


class GuardianPatchedObjectPermissionChecker(ObjectPermissionChecker):
    def get_perms(self, obj):
        perms = super(GuardianPatchedObjectPermissionChecker, self).get_perms(obj)
        print(perms)
        return perms
