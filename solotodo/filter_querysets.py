from django.db.models import Q
from guardian.shortcuts import get_objects_for_user

from solotodo.models import Store, Category, Entity


def stores__view_store_update_logs(request):
    if request:
        return get_objects_for_user(request.user, 'view_store_update_logs',
                                    klass=Store)
    return Store.objects.all()


def stores__view(request, qs=None):
    if not qs:
        qs = Store.objects.all()

    if request:
        return get_objects_for_user(
            request.user, 'view_store', qs)

    return qs


def stores__view_stocks(request):
    if request:
        return get_objects_for_user(
            request.user, 'view_store_stocks', Store)
    return Store.objects.all()


def categories__view(request):
    if request:
        return get_objects_for_user(request.user, 'view_category', Category)
    return Category.objects.all()


def categories__view_stocks(request):
    if request:
        return get_objects_for_user(request.user, 'view_category_stocks',
                                    Category)
    return Category.objects.all()
