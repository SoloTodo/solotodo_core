from guardian.core import ObjectPermissionChecker
from guardian.shortcuts import get_perms
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet


class PermissionListModelMixin(object):
    """
    Reimplements DRF List Mixin to include user permission for its objects
    """
    def list(self, request, *args, **kwargs):
        # Copy-paste of old implementation
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)

        # Add user permissions

        perms_checker = ObjectPermissionChecker(request.user)
        perms_checker.prefetch_perms(queryset)

        response_data = serializer.data

        for idx, obj in enumerate(queryset):
            response_data[idx]['permissions'] = perms_checker.get_perms(obj)

        return Response(response_data)


class PermissionRetrieveModelMixin(object):
    """
    Reimplements DRF Retrieve Mixin to include user permission for the object
    """
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)

        response_data = serializer.data

        # Add permissions

        response_data['permissions'] = get_perms(request.user, instance)

        return Response(response_data)


class PermissionReadOnlyModelViewSet(PermissionRetrieveModelMixin,
                                     PermissionListModelMixin,
                                     GenericViewSet):
    """
    Variation of DRF ReadOnlyModelViewSet that includes user permissions
    for the objects it retrieves
    """
    pass
