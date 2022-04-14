from django import forms
from django.contrib.auth.models import AnonymousUser
from guardian.core import ObjectPermissionChecker
from guardian.shortcuts import get_objects_for_user

from category_templates.models import CategoryTemplate
from category_templates.serializers import CategoryTemplateSerializer
from solotodo.models import Country, Currency, StoreType, Store, \
    NumberFormat, Category, Language
from solotodo.serializers import CountrySerializer, CurrencySerializer, \
    StoreTypeSerializer, StoreSerializer, NumberFormatSerializer, \
    CategorySerializer, LanguageSerializer


class ResourceNamesForm(forms.Form):
    model_map = {
        'languages': {
            'model': Language,
            'serializer': LanguageSerializer,
            'permission': None,
            'has_permissions': False
        },
        'countries': {
            'model': Country,
            'serializer': CountrySerializer,
            'permission': None,
            'has_permissions': False
        },
        'currencies': {
            'model': Currency,
            'serializer': CurrencySerializer,
            'permission': None,
            'has_permissions': False
        },
        'store_types': {
            'model': StoreType,
            'serializer': StoreTypeSerializer,
            'permission': None,
            'has_permissions': False
        },
        'stores': {
            'model': Store,
            'serializer': StoreSerializer,
            'permission': 'view_store',
            'has_permissions': True
        },
        'number_formats': {
            'model': NumberFormat,
            'serializer': NumberFormatSerializer,
            'permission': None,
            'has_permissions': False
        },
        'categories': {
            'model': Category,
            'serializer': CategorySerializer,
            'permission': 'view_category',
            'has_permissions': True
        },
        'category_templates': {
            'model': CategoryTemplate,
            'serializer': CategoryTemplateSerializer,
            'permission': None,
            'has_permissions': False
        }
    }

    choices = [(key, key) for key in model_map.keys()]

    names = forms.MultipleChoiceField(
        choices=choices,
        required=False
    )

    def get_objects(self, request, include_permissions=False):
        resource_names = self.cleaned_data['names']
        if not resource_names:
            resource_names = [choice[0] for choice in
                              ResourceNamesForm.choices]

        if include_permissions:
            user = request.user
        else:
            user = AnonymousUser()

        perms_checker = ObjectPermissionChecker(user)
        response = []

        for resource_name in resource_names:
            resource_model_and_serializer = \
                ResourceNamesForm.model_map[resource_name]
            model = resource_model_and_serializer['model']
            serializer = resource_model_and_serializer['serializer']

            if resource_model_and_serializer['permission']:
                model_objects = get_objects_for_user(
                    user, resource_model_and_serializer['permission'],
                    klass=model)
            else:
                model_objects = model.objects.all()

            resource_entries = serializer(model_objects, many=True,
                                          context={'request': request})

            if include_permissions and \
                    resource_model_and_serializer['has_permissions']:
                perms_checker.prefetch_perms(model_objects)
                for idx, entry in enumerate(resource_entries.data):
                    entry['permissions'] = perms_checker.get_perms(
                        model_objects[idx])

            response.extend(resource_entries.data)
        return response
