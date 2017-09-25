from solotodo.models import Store, Category, Product, Entity


def create_model_filter(model, default_permission):
    def model_filter(permission=default_permission, qs=None):
        if qs is None:
            qs = model.objects.all()

        def inner_filter(request=None):
            if request:
                return qs.filter_by_user_perms(request.user, permission)
            return qs

        return inner_filter
    return model_filter


create_store_filter = create_model_filter(Store, 'view_store')
create_category_filter = create_model_filter(Category, 'view_category')
create_product_filter = create_model_filter(Product, 'view_product')
create_entity_filter = create_model_filter(Entity, 'view_entity')
