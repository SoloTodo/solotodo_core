from django.db.models import Q
from guardian.shortcuts import get_objects_for_user

from solotodo.models import Store, Category, Entity


def stores__view_store_update_logs(request):
    if request:
        return get_objects_for_user(request.user, 'view_store_update_logs',
                                    klass=Store)
    return Store.objects.all()


def stores__view_store_entities(request):
    if request:
        return get_objects_for_user(
            request.user, 'view_store_entities', Store)
    return Store.objects.all()


def stores__view_store(request):
    if request:
        return get_objects_for_user(
            request.user, 'view_store', Store)
    return Store.objects.all()


def categories__view_category_entities(request):
    if request:
        return get_objects_for_user(
            request.user, 'view_category_entities', Category)
    return Category.objects.all()


def categories__view_category_products(request):
    if request:
        return get_objects_for_user(request.user, 'view_category_products',
                                    Category)
    return Category.objects.all()


def entities__view(request):
    if request:
        categories_with_permission = get_objects_for_user(
            request.user, 'view_category_entities', Category)
        stores_with_permission = get_objects_for_user(
            request.user, 'view_store_entities', Store)

        return Entity.objects.filter(
            Q(category__in=categories_with_permission) &
            Q(store__in=stores_with_permission)).select_related()
    return Entity.objects.all().select_related()
