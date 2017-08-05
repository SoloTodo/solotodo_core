from rest_framework.exceptions import PermissionDenied


def detail_permission(permission_name):
    def decorator(func):
        def permissions_decorator(self, request, pk, *args, **kwargs):
            obj = self.get_object()
            if request.user.has_perm(permission_name, obj):
                return func(self, request, pk, *args, **kwargs)
            else:
                raise PermissionDenied

        return permissions_decorator

    return decorator
