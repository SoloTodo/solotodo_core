# coding=utf-8
import json
import os
from django.conf import settings
from django.contrib import messages
from django.core.files.storage import default_storage
from django.http import HttpResponseRedirect, HttpResponse
from django.urls import reverse_lazy, reverse
from django.views.generic import ListView, DetailView, FormView
from django_filters import rest_framework
from rest_framework import viewsets
from rest_framework.filters import SearchFilter
from rest_framework.permissions import IsAdminUser, BasePermission

from metamodel.filters import InstanceFilterSet
from metamodel.forms.meta_field_form import MetaFieldForm
from metamodel.forms.meta_field_make_non_nullable_meta_field_form import \
    MetaFieldMakeNonNullableMetaFieldForm
from metamodel.forms.meta_field_make_non_nullable_primitive_form import \
    MetaFieldMakeNonNullablePrimitiveForm
from metamodel.forms.meta_model_add_field_form import MetaModelAddFieldForm
from metamodel.forms.meta_model_form import MetaModelForm
from metamodel.models import MetaModel, MetaField, InstanceModel
from metamodel.pagination import InstancePagination
from metamodel.plugin import Plugin
from metamodel.serializers import MetaModelWithoutFieldsSerializer, \
    MetaModelSerializer, InstanceSerializer


class ModelListView(ListView):
    queryset = MetaModel.get_non_primitive()
    template_name = 'metamodel/model_list.html'


class ModelDetailView(DetailView):
    queryset = MetaModel.get_non_primitive()
    template_name = 'metamodel/model_detail.html'


class ModelAddView(FormView):
    form_class = MetaModelForm
    template_name = 'metamodel/model_add.html'
    success_url = reverse_lazy('metamodel_model_list')

    def form_valid(self, form):
        form.save()

        self.meta_model = form.instance

        return super(ModelAddView, self).form_valid(form)

    def get_success_url(self):
        return reverse('metamodel_model_meta',
                       kwargs={'pk': self.meta_model.pk})


class ModelEditView(DetailView):
    queryset = MetaModel.get_non_primitive()
    template_name = 'metamodel/model_edit.html'

    def get_context_data(self, **kwargs):
        context = super(ModelEditView, self).get_context_data(**kwargs)

        form = MetaModelForm(instance=self.object)
        context['form'] = form

        return context

    def post(self, request, pk, *args, **kwargs):
        meta_model = self.get_object()

        form = MetaModelForm(request.POST, instance=meta_model)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(
                reverse('metamodel_model_meta',
                        kwargs={'pk': self.get_object().pk}))
        else:
            self.object = meta_model
            context = self.get_context_data(**kwargs)
            context['form'] = form
            return self.render_to_response(context)


class ModelDeleteView(DetailView):
    queryset = MetaModel.get_non_primitive()
    template_name = 'metamodel/model_delete.html'

    def post(self, request, pk, *args, **kwargs):
        meta_model = self.get_object()
        meta_model.delete()

        return HttpResponseRedirect(reverse('metamodel_model_list'))


class ModelMetaView(DetailView):
    queryset = MetaModel.get_non_primitive()
    template_name = 'metamodel/model_meta.html'

    def post(self, request, pk, *args, **kwargs):
        meta_model = self.get_object()

        for field in meta_model.fields.all():
            if field.name in request.POST:
                field.ordering = int(request.POST[field.name])
                field.save()

        return HttpResponseRedirect(reverse('metamodel_model_meta',
                                            kwargs={'pk': meta_model.pk}))


class ModelAddInstance(DetailView):
    queryset = MetaModel.get_non_primitive()
    template_name = 'metamodel/model_add_instance.html'

    def is_popup(self):
        return bool(self.request.GET.get('popup', False))

    def get_context_data(self, **kwargs):
        context = super(ModelAddInstance, self).get_context_data(**kwargs)
        context['form'] = self.object.get_form()()
        is_popup = self.is_popup()

        form_action = reverse('metamodel_model_add_instance',
                              kwargs={'pk': self.object.pk})

        if is_popup:
            form_action += '?popup=1'

        context['hide_nav'] = is_popup
        context['form_action'] = form_action
        return context

    def post(self, request, pk, *args, **kwargs):
        meta_model = self.get_object()

        form = meta_model.get_form()(request.POST, request.FILES)

        if form.is_valid():
            instance_model = InstanceModel()
            instance_model.model = meta_model

            instance_model.save(initial=True)
            instance_model.update_fields(
                form.cleaned_data,
                request.POST,
                creator_id=request.user.id)

            if self.is_popup():
                return HttpResponseRedirect(reverse(
                    'metamodel_instance_popup_redirect',
                    kwargs={'pk': instance_model.pk}))
            else:
                messages.success(
                    request,
                    u'<a href={0}>{1}</a> creada correctamente'.format(
                        reverse('metamodel_instance_detail',
                                kwargs={'pk': instance_model.pk}),
                        str(instance_model)
                    ))
                return HttpResponseRedirect(reverse(
                    'metamodel_model_detail', kwargs={'pk': meta_model.pk}))
        else:
            self.object = meta_model
            context = self.get_context_data(**kwargs)
            context['form'] = form
            return self.render_to_response(context)


class ModelUsagesView(DetailView):
    queryset = MetaModel.get_non_primitive()
    template_name = 'metamodel/model_usages.html'


class MetaModelAddFieldView(DetailView):
    queryset = MetaModel.get_non_primitive()
    template_name = 'metamodel/model_add_field.html'

    def get(self, request, *args, **kwargs):
        if request.is_ajax():
            model_type = request.GET['model']
            nullable = request.GET['nullable'] == 'true'
            multiple = request.GET['multiple'] == 'true'

            meta_model = self.get_object()

            requires_default = True

            if nullable or multiple:
                requires_default = False

            if not meta_model.instancemodel_set.all():
                requires_default = False

            default_choices = None

            if model_type:
                meta_model = MetaModel.objects.get(pk=model_type)
                if meta_model.is_primitive():
                    default_choices = meta_model.html_input_type()
                else:
                    default_choices = [(e.pk, str(e)) for e
                                       in meta_model.instancemodel_set.all()]

            return HttpResponse(json.dumps([requires_default,
                                            default_choices]))

        else:
            return super(MetaModelAddFieldView, self).get(request, *args,
                                                          **kwargs)

    def get_context_data(self, **kwargs):
        context = super(MetaModelAddFieldView, self).get_context_data(**kwargs)

        form = MetaModelAddFieldForm()
        context['form'] = form

        return context

    def post(self, request, pk, *args, **kwargs):
        meta_model = self.get_object()

        form = MetaModelAddFieldForm(data=request.POST, files=request.FILES)

        if form.is_valid():
            meta_field = form.instance
            meta_field.parent = meta_model

            if meta_field.requires_default_value_for_saving():
                if meta_field.model.name == 'FileField':
                    default_value = request.FILES['default'].name
                    cleaned_default = meta_field.clean_value(default_value)

                    if hasattr(settings, 'METAMODEL'):
                        path = os.path.join(
                            settings.METAMODEL.get('MEDIA_PATH', ''),
                            cleaned_default)
                    else:
                        path = cleaned_default

                    cleaned_default = default_storage.save(
                        path, request.FILES['default'])
                else:
                    default_value = request.POST.get('default')
                    cleaned_default = meta_field.clean_value(default_value)

                meta_field.save(default=cleaned_default)
            else:
                meta_field.save()

            return HttpResponseRedirect(reverse('metamodel_model_meta',
                                                kwargs={'pk': meta_model.pk}))

        self.object = meta_model
        context = self.get_context_data(**kwargs)
        context['form'] = form
        return self.render_to_response(context)


class MetaFieldDetailView(DetailView):
    model = MetaField
    template_name = 'metamodel/field_detail.html'

    def get_context_data(self, **kwargs):
        context = super(MetaFieldDetailView, self).get_context_data(**kwargs)

        context['form'] = MetaFieldForm(instance=self.object)

        return context

    def post(self, request, pk, *args, **kwargs):
        meta_field = self.get_object()
        form = MetaFieldForm(request.POST, instance=meta_field)

        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse(
                'metamodel_model_meta',
                kwargs={'pk': meta_field.parent.pk}))
        else:
            self.object = meta_field
            context = self.get_context_data()
            context['form'] = form

            return self.render_to_response(context)


class MetaFieldDeleteView(DetailView):
    model = MetaField
    template_name = 'metamodel/field_delete.html'

    def post(self, request, pk, *args, **kwargs):
        meta_field = self.get_object()

        meta_model = meta_field.parent
        meta_field.delete()

        return HttpResponseRedirect(reverse(
            'metamodel_model_meta',
            kwargs={'pk': meta_model.pk}))


class MetaFieldMakeNullableView(DetailView):
    queryset = MetaField.objects.filter(nullable=False)
    template_name = 'metamodel/field_make_nullable.html'

    def post(self, request, pk, *args, **kwargs):
        meta_field = self.get_object()
        meta_field.nullable = True
        meta_field.save()

        return HttpResponseRedirect(reverse(
            'metamodel_model_meta',
            kwargs={'pk': meta_field.parent.pk}))


class MetaFieldMakeNonNullableView(DetailView):
    queryset = MetaField.objects.filter(nullable=True)
    template_name = 'metamodel/field_make_non_nullable.html'

    def get_form(self, data=None):
        meta_field = self.get_object()
        form = None
        if not meta_field.multiple:
            if meta_field.model.is_primitive():
                form = MetaFieldMakeNonNullablePrimitiveForm(meta_field,
                                                             data=data)
            else:
                form = MetaFieldMakeNonNullableMetaFieldForm(meta_field,
                                                             data=data)

        return form

    def get_context_data(self, **kwargs):
        context = super(MetaFieldMakeNonNullableView, self).get_context_data(
            **kwargs)

        form = self.get_form()
        context['form'] = form

        return context

    def post(self, request, pk, *args, **kwargs):
        meta_field = self.get_object()

        form = self.get_form(data=self.request.POST)

        if form:
            if form.is_valid():
                default = form.cleaned_data['default']
                meta_field.nullable = False
                meta_field.save(default=default)
            else:
                self.object = meta_field
                context = self.get_context_data()
                context['form'] = form

                return self.render_to_response(context)
        else:
            meta_field.nullable = False
            meta_field.save()

        return HttpResponseRedirect(reverse(
            'metamodel_model_meta',
            kwargs={'pk': meta_field.parent.pk}))


class MetaFieldMakeMultipleView(DetailView):
    queryset = MetaField.objects.filter(multiple=False)
    template_name = 'metamodel/field_make_multiple.html'

    def post(self, request, pk, *args, **kwargs):
        meta_field = self.get_object()
        meta_field.multiple = True
        meta_field.save()

        return HttpResponseRedirect(reverse(
            'metamodel_model_meta',
            kwargs={'pk': meta_field.parent.pk}))


class InstanceModelDetailView(DetailView):
    queryset = InstanceModel.get_non_primitive()
    template_name = 'metamodel/instance_detail.html'

    def get_context_data(self, **kwargs):
        context = super(InstanceModelDetailView, self).get_context_data(
            **kwargs)

        instance_model = self.get_object()
        form_klass = instance_model.get_form()

        context['form'] = form_klass()

        plugin_context = []
        for PluginKlass in Plugin.registry.values():
            plugin_value = PluginKlass.on_instance_model_detail_view(
                instance_model)
            if plugin_value is not None:
                plugin_context.append(plugin_value)

        context['plugin_context'] = plugin_context

        return context

    def post(self, request, pk, *args, **kwargs):
        instance_model = self.get_object()

        form = instance_model.get_form()(request.POST, request.FILES)

        if form.is_valid():
            instance_model.update_fields(form.cleaned_data, request.POST)
            messages.success(
                request,
                u'<a href={0}>{1}</a> actualizado correctamente'.format(
                    reverse('metamodel_instance_detail',
                            kwargs={'pk': instance_model.pk}),
                    str(instance_model)
                ))
            if 'save' in request.POST:
                return HttpResponseRedirect(
                    reverse('metamodel_model_detail',
                            kwargs={'pk': instance_model.model.pk}))

            return HttpResponseRedirect(
                reverse('metamodel_instance_detail',
                        kwargs={'pk': instance_model.pk}))

        else:
            messages.error(request, u'Formulario no válido')
            self.object = instance_model
            context = self.get_context_data(**kwargs)
            context['form'] = form

            return self.render_to_response(context)


class InstanceModelDeleteView(DetailView):
    queryset = InstanceModel.get_non_primitive()
    template_name = 'metamodel/instance_delete.html'

    def post(self, request, pk, *args, **kwargs):
        instance_model = self.get_object()
        model = instance_model.model

        instance_model.delete()
        messages.success(request, u'Instancia borrada correctamente')

        return HttpResponseRedirect(reverse('metamodel_model_detail',
                                            kwargs={'pk': model.id}))


class InstanceModelPopupRedirect(DetailView):
    queryset = InstanceModel.get_non_primitive()
    template_name = 'metamodel/instance_popup_redirect.html'

    def get_context_data(self, **kwargs):
        context = super(InstanceModelPopupRedirect, self).get_context_data(
            **kwargs)

        instance_dict = {
            'id': self.object.id,
            'name': str(self.object),
            'model': self.object.model.id
        }

        context['instance_json'] = json.dumps(instance_dict)

        return context


class MetaModelViewSet(viewsets.ModelViewSet):
    queryset = MetaModel.objects.all()
    permission_classes = [IsAdminUser]

    def get_serializer_class(self):
        if self.action == 'list' or self.action == 'create':
            return MetaModelWithoutFieldsSerializer
        if self.action == 'retrieve':
            return MetaModelSerializer

    def get_permissions(self):
        if self.action == 'create':
            self.permission_classes = [IsSuperUser, ]
        elif self.action == 'list' or self.action == 'retrieve':
            self.permission_classes = [IsAdminUser]
        return super(self.__class__, self).get_permissions()


class IsSuperUser(BasePermission):

    def has_permission(self, request, view):
        return request.user and request.user.is_superuser


class InstanceModelViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = InstanceModel.objects.all()
    pagination_class = InstancePagination
    serializer_class = InstanceSerializer
    filter_backends = (rest_framework.DjangoFilterBackend, SearchFilter)
    filter_class = InstanceFilterSet
