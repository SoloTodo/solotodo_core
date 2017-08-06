from django.conf.urls import url
from metamodel.views import ModelListView, ModelDetailView, ModelMetaView, \
    MetaFieldDetailView, MetaFieldMakeNullableView, \
    MetaFieldMakeNonNullableView, ModelAddView, ModelEditView, \
    ModelDeleteView, MetaModelAddFieldView, MetaFieldDeleteView, \
    InstanceModelDetailView, ModelAddInstance, InstanceModelDeleteView, \
    InstanceModelPopupRedirect, MetaFieldMakeMultipleView, ModelUsagesView


def staff_login_required(f):
    from django.contrib.auth.views import redirect_to_login

    def wrap(request, *args, **kwargs):
        if not request.user.is_authenticated() or not request.user.is_staff:
            return redirect_to_login(request.get_full_path())

        return f(request, *args, **kwargs)

    return wrap


def superuser_required(function=None, redirect_field_name='next',
                       login_url=None):
    from django.contrib.auth.decorators import user_passes_test

    actual_decorator = user_passes_test(
        lambda u: u.is_authenticated() and u.is_superuser,
        login_url=login_url,
        redirect_field_name=redirect_field_name
    )
    if function:
        return actual_decorator(function)
    return actual_decorator


urlpatterns = [
    url('models/$',
        staff_login_required(ModelListView.as_view()),
        name='metamodel_model_list'),
    url('models/add/$',
        superuser_required(ModelAddView.as_view()),
        name='metamodel_model_add'),
    url('models/(?P<pk>\d+)/delete/$',
        superuser_required(ModelDeleteView.as_view()),
        name='metamodel_model_delete'),
    url('models/(?P<pk>\d+)/$',
        staff_login_required(ModelDetailView.as_view()),
        name='metamodel_model_detail'),
    url('models/(?P<pk>\d+)/edit/$',
        superuser_required(ModelEditView.as_view()),
        name='metamodel_model_edit'),
    url('models/(?P<pk>\d+)/meta/$',
        superuser_required(ModelMetaView.as_view()),
        name='metamodel_model_meta'),
    url('models/(?P<pk>\d+)/add_field/$',
        superuser_required(MetaModelAddFieldView.as_view()),
        name='metamodel_model_add_field'),
    url('models/(?P<pk>\d+)/add_instance/$',
        staff_login_required(ModelAddInstance.as_view()),
        name='metamodel_model_add_instance'),
    url('models/(?P<pk>\d+)/usages/$',
        superuser_required(ModelUsagesView.as_view()),
        name='metamodel_model_usages'),
    url('fields/(?P<pk>\d+)/$',
        superuser_required(MetaFieldDetailView.as_view()),
        name='metamodel_field_detail'),
    url('fields/(?P<pk>\d+)/delete/$',
        superuser_required(MetaFieldDeleteView.as_view()),
        name='metamodel_field_delete'),
    url('fields/(?P<pk>\d+)/make_nullable/$',
        superuser_required(MetaFieldMakeNullableView.as_view()),
        name='metamodel_field_make_nullable'),
    url('fields/(?P<pk>\d+)/make_multiple/$',
        superuser_required(MetaFieldMakeMultipleView.as_view()),
        name='metamodel_field_make_multiple'),
    url('fields/(?P<pk>\d+)/make_non_nullable/$',
        superuser_required(MetaFieldMakeNonNullableView.as_view()),
        name='metamodel_field_make_non_nullable'),
    url('instances/(?P<pk>\d+)/$',
        staff_login_required(InstanceModelDetailView.as_view()),
        name='metamodel_instance_detail'),
    url('instances/(?P<pk>\d+)/delete/$',
        staff_login_required(InstanceModelDeleteView.as_view()),
        name='metamodel_instance_delete'),
    url('instances/(?P<pk>\d+)/popup_redirect/$',
        staff_login_required(InstanceModelPopupRedirect.as_view()),
        name='metamodel_instance_popup_redirect'),
]
