from rest_framework.permissions import BasePermission


class BudgetPermission(BasePermission):
    def has_permission(self, request, view):
        print(view.action)
        if view.action in ['list', 'retrieve', 'export']:
            return True

        if view.action in ['create', 'update', 'partial_update',
                           'destroy', 'add_product', 'select_cheapest_stores',
                           'compatibility_issues'] \
                and request.user.is_authenticated:
            return True

        return False

    def has_object_permission(self, request, view, obj):
        user = request.user

        if user.is_superuser:
            return True

        if view.action in ['retrieve', 'export'] and obj.is_public:
            return True

        if not user.is_authenticated:
            return False

        if obj.user == user:
            return True

        return False
