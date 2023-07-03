from django.apps import AppConfig


class SolotodoConfig(AppConfig):
    name = 'solotodo'

    def ready(self):
        # Monkey patch guardian's ObjectPermissionChecker to fix an issue where
        # general permissions would not apply to individual objects
        from guardian import core
        from solotodo_core.guardian_patched_object_permission_checker import \
            GuardianPatchedObjectPermissionChecker

        core.ObjectPermissionChecker = GuardianPatchedObjectPermissionChecker
