import calendar
import json
import time
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
import importlib

from PIL import Image
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.template import Template, Context
import os
from django.conf import settings
from django.core.files import File
from django.core.files.storage import default_storage
from django.db import models, IntegrityError
from django.db.models import Q, FileField
from django.db.models.fields.files import FieldFile
from metamodel.models import MetaModel, MetaField
from metamodel.signals import instance_model_saved
from metamodel.utils import strip_whitespace, trim, \
    convert_image_to_inmemoryfile


class InstanceModelQuerySet(models.QuerySet):
    def get_field_values(self, field):
        from metamodel.models import InstanceField

        instance_fields = InstanceField.objects.filter(
            parent__in=self,
            field__name=field
        ).select_related('parent', 'value')

        return {instance_field.parent: instance_field.value.value
                for instance_field in instance_fields}


class InstanceModel(models.Model):
    decimal_value = models.DecimalField(max_digits=200, decimal_places=5,
                                        null=True, blank=True)
    unicode_value = models.CharField(max_length=1024, null=True, blank=True)
    unicode_representation = models.CharField(max_length=255, null=True,
                                              blank=True)
    model = models.ForeignKey(MetaModel, on_delete=models.CASCADE)

    objects = InstanceModelQuerySet.as_manager()

    METAMODEL_METAFIELDS_DICT = None

    def _get_value(self):
        primitive_models_dict = MetaModel.get_primitive_models_dict()

        mtype = primitive_models_dict.get(self.model_id, None)

        if mtype:
            mtype = mtype.name

            if mtype == 'BooleanField':
                return bool(self.decimal_value)
            if mtype == 'CharField':
                return self.unicode_value
            if mtype == 'DateField':
                return date.fromordinal(self.decimal_value)
            if mtype == 'DateTimeField':
                epoch = datetime.utcfromtimestamp(0)
                delta = timedelta(seconds=int(self.decimal_value))
                return epoch + delta
            if mtype == 'DecimalField':
                return self.decimal_value
            if mtype == 'FileField':
                return FieldFile(default_storage.open(self.unicode_value),
                                 FileField(), self.unicode_value)
            if mtype == 'IntegerField':
                return int(self.decimal_value)

        return self.__getattr__('value')

    def _set_value(self, new_value):
        mtype = MetaModel.get_primitive_models_dict()[self.model_id].name

        if mtype == 'BooleanField':
            if not isinstance(new_value, bool):
                raise ValueError

            self.decimal_value = int(new_value)
            self.unicode_value = None

        if mtype == 'CharField':
            if not isinstance(new_value, str):
                raise ValueError

            self.unicode_value = str(new_value)
            self.decimal_value = None

        if mtype == 'DateField':
            if not isinstance(new_value, date):
                raise ValueError

            self.decimal_value = new_value.toordinal()
            self.unicode_value = None

        if mtype == 'DateTimeField':
            if not isinstance(new_value, datetime):
                raise ValueError

            epoch = datetime.utcfromtimestamp(0)

            self.decimal_value = (new_value.replace(tzinfo=None) -
                                  epoch).total_seconds()
            self.unicode_value = None

        if mtype == 'DecimalField':
            self.decimal_value = Decimal(new_value)
            self.unicode_value = None

        if mtype == 'FileField':
            if isinstance(new_value, File):
                self.unicode_value = new_value.name
                self.decimal_value = None
                return

            if not isinstance(new_value, str):
                raise ValueError

            self.unicode_value = str(new_value)
            self.decimal_value = None

        if mtype == 'IntegerField':
            if not isinstance(new_value, int):
                raise ValueError

            self.decimal_value = new_value
            self.unicode_value = None

    value = property(_get_value, _set_value)

    def is_model_primitive(self):
        primitive_models_dict = MetaModel.get_primitive_models_dict()
        return self.model_id in primitive_models_dict

    def __str__(self):
        if not self.is_model_primitive():
            if self.unicode_representation:
                return self.unicode_representation
            else:
                return '[No unicode representation]'.format(self.model)

        else:
            return str(self.value)

    def get_unicode_representation(self):
        # 1. Custom logic for unicode representation?
        if hasattr(settings, 'METAMODEL'):
            unicode_functions_paths = \
                settings.METAMODEL.get('UNICODE_FUNCTIONS', [])
            for path in unicode_functions_paths:
                path_components = path.split('.')
                module = importlib.import_module(
                    '.'.join(path_components[:-1]))
                unicode_function = getattr(module, path_components[-1])
                result = unicode_function(self)
                if result:
                    return strip_whitespace(result)

        # 2. MetaModel unicode template field?
        if self.model.unicode_template:
            result = Template(self.model.unicode_template).render(Context({
                'im': self
            }))
            return strip_whitespace(result)

        # Nothing found

        return None

    def save(self, *args, **kwargs):
        if not self.unicode_representation:
            self.unicode_representation = None

        initial = kwargs.pop(
            'initial', False)

        creator_id = kwargs.pop(
            'creator_id', None)

        if not initial:
            if settings.METAMODEL['DEBUG']:
                # Check integrity
                for instance_field in self.fields.select_related():
                    if not instance_field.field.multiple and \
                            not instance_field.field.nullable:
                        if instance_field.value is None:
                            raise IntegrityError(
                                '{} is a required field of {}'
                                ''.format(instance_field.field.name,
                                          self.model))

            self.unicode_representation = self.get_unicode_representation()

            if not self.is_model_primitive():
                ordering_value = self.compute_ordering_value()
                try:
                    ordering_value = Decimal(str(ordering_value))
                    self.decimal_value = ordering_value
                except InvalidOperation:
                    self.unicode_value = str(ordering_value)

        if not self.unicode_value:
            self.unicode_value = None

        if self.is_model_primitive() and \
                self.unicode_representation is not None:
            raise IntegrityError('Primitive values cannot have unicode '
                                 'representations')

        if self.model.name == 'BooleanField':
            if self.decimal_value not in [0, 1]:
                raise IntegrityError

            self.unicode_value = None

        if self.model.name == 'CharField':
            if not isinstance(self.unicode_value, str) \
                    and not isinstance(self.unicode_value, str):
                raise IntegrityError

            self.decimal_value = None

        if self.model.name == 'IntegerField':
            if self.decimal_value is None:
                raise IntegrityError

            self.unicode_value = None

        if self.model.name == 'DateField':
            if self.decimal_value is None:
                raise IntegrityError

            try:
                date.fromordinal(self.decimal_value)
            except ValueError:
                raise IntegrityError

            self.unicode_value = None

        if self.model.name == 'DateTimeField':
            if self.decimal_value is None:
                raise IntegrityError

            try:
                epoch = datetime.utcfromtimestamp(0)
                epoch + timedelta(seconds=int(self.decimal_value))
            except (OverflowError, ValueError):
                raise IntegrityError

            self.unicode_value = None

        if self.model.name == 'FileField':
            if not isinstance(self.unicode_value, str):
                raise IntegrityError

            self.decimal_value = None

        if self.model.name == 'IntegerField':
            if not isinstance(self.decimal_value, int) and \
                    not isinstance(self.decimal_value, Decimal):
                raise IntegrityError

            self.unicode_value = None

        created = not bool(self.id)
        result = super(InstanceModel, self).save(*args, **kwargs)

        if not initial:
            instance_model_saved.send(
                sender=self.__class__,
                instance_model=self,
                created=created,
                creator_id=creator_id
            )

        return result

    def delete(self, *args, **kwargs):
        primitive_instance_fields = self.fields.filter(
            value__model__in=MetaModel.get_primitive())

        for field in primitive_instance_fields:
            field.value.delete()

        return super(InstanceModel, self).delete(*args, **kwargs)

    @classmethod
    def get_non_primitive(cls):
        return cls.objects.filter(
            ~Q(model__name__in=MetaModel.NAME_INPUT_TYPES_DICT.keys()))

    def get_form(self):
        form_klass = self.model.get_form()

        for field in self.model.fields.filter(hidden=False):
            form_klass.base_fields[field.name].initial = \
                getattr(self, field.name)

        return form_klass

    def __setattr__(self, name, value):
        if name in ['id', 'decimal_value', 'unicode_value',
                    'unicode_representation', 'model_id', 'model']:
            return super(InstanceModel, self).__setattr__(name, value)

        primitive_models_dict = MetaModel.get_primitive_models_dict()

        if name == 'value' and self.model_id in primitive_models_dict:
            self._set_value(value)
            return

        if name.startswith('_'):
            return super(InstanceModel, self).__setattr__(name, value)

        from metamodel.models import InstanceField

        try:
            mf = MetaField.objects.get(parent=self.model, name=name)

            is_primitive = mf.model_id in primitive_models_dict

            if not mf.nullable and not mf.multiple and not is_primitive:
                if value is None:
                    raise IntegrityError('This field cannot be None')

                InstanceField.get_or_create_with_value(self, mf, value)
            if not mf.nullable and not mf.multiple and is_primitive:
                if value is None:
                    raise IntegrityError('This field cannot be None')

                InstanceField.get_or_create_with_value(self, mf, value)
            if mf.multiple and not is_primitive:
                InstanceField.objects.filter(field=mf, parent=self).delete()
                for individual_value in value:
                    new_field = InstanceField(
                        parent=self,
                        field=mf,
                    )

                    new_field.value = individual_value
                    new_field.save()

            if mf.multiple and is_primitive:
                existing_fields = InstanceField.objects.filter(field=mf,
                                                               parent=self)
                for field in existing_fields:
                    field.value.delete()

                for individual_value in value:
                    im = InstanceModel(model=mf.model)
                    im.value = individual_value
                    im.save()

                    new_field = InstanceField(
                        parent=self,
                        field=mf,
                    )

                    new_field.value = im
                    new_field.save()

            if mf.nullable and not mf.multiple and not is_primitive:
                InstanceField.get_or_create_with_value(self, mf, value)

            if mf.nullable and not mf.multiple and is_primitive:
                InstanceField.get_or_create_with_value(self, mf, value)

        except MetaField.DoesNotExist:
            return object.__setattr__(self, name, value)

    @classmethod
    def get_metafield_by_parent_model_id_and_field_name(
            cls, model_id, field_name):

        def get_metafields_dict(refresh_cache=False):
            result = cls.METAMODEL_METAFIELDS_DICT
            if result is None or refresh_cache:
                meta_fields = MetaField.objects.select_related()
                result = {(field.parent_id, field.name): field
                          for field in meta_fields}
                cls.METAMODEL_METAFIELDS_DICT = result

            return result

        meta_field_dict = get_metafields_dict()
        meta_field = meta_field_dict.get((model_id, field_name), None)
        if meta_field:
            return meta_field
        else:
            meta_field_dict = get_metafields_dict(refresh_cache=True)
            return meta_field_dict[(model_id, field_name)]

    def __getattr__(self, item):
        # Prevent clashing with django's lookups (e.g. "_model_cache")
        if item.startswith('_'):
            raise AttributeError

        if item == 'field':
            return getattr(super(InstanceModel, self), item)

        if item == 'model':
            raise AttributeError('Model for this instance is not specified')

        if item in ['as_sql', 'is_compatible_query_object_type',
                    'get_compiler', 'resolve_expression', 'query',
                    'bump_prefix']:
            raise AttributeError

        meta_field = self.get_metafield_by_parent_model_id_and_field_name(
            self.model_id, item)

        instance_fields = self.fields.filter(field=meta_field).select_related()

        if meta_field.multiple:
            if not self.is_model_primitive():
                return [f.value for f in instance_fields]
            else:
                return [f.value.value for f in instance_fields]
        else:
            if instance_fields:
                if meta_field.model.is_primitive():
                    return instance_fields[0].value.value
                else:
                    return instance_fields[0].value
            else:
                return None

    def update_fields(self, form_cleaned_data, data, creator_id=None):
        for field in self.model.fields.filter(hidden=False):
            cleaned_value = form_cleaned_data[field.name]

            if field.model.name == 'FileField':
                clear_value = data.get(field.name + '-clear', None)

                if clear_value:
                    cleaned_value = None
                else:
                    uploaded_file = form_cleaned_data[field.name]

                    if isinstance(uploaded_file, InMemoryUploadedFile):
                        uploaded_image = Image.open(uploaded_file)
                        uploaded_image = trim(uploaded_image)

                        extension = uploaded_file.name.split('.')[-1]

                        new_filename = '{0}_{1}_{2}.{3}'.format(
                            self.id,
                            field.name,
                            calendar.timegm(time.gmtime()),
                            extension)

                        if hasattr(settings, 'METAMODEL'):
                            path = os.path.join(
                                settings.METAMODEL.get('MEDIA_PATH', ''),
                                new_filename)
                        else:
                            path = new_filename

                        new_uploaded_file = convert_image_to_inmemoryfile(
                            uploaded_image)

                        cleaned_value = default_storage.save(
                            path, new_uploaded_file)

            if cleaned_value == '':
                cleaned_value = None
            setattr(self, field.name, cleaned_value)
        self.save(creator_id=creator_id)

    def get_ordering_value(self):
        if self.decimal_value is not None:
            return self.decimal_value
        return self.unicode_value

    def compute_ordering_value(self):
        from metamodel.models import InstanceField

        if self.is_model_primitive():
            result = self.value
            model_name = self.model.name
            if model_name == 'BooleanField':
                return int(result)
            if model_name in ['CharField', 'DecimalField', 'IntegerField']:
                return result
            if model_name == 'DateField':
                return result.toordinal()

            if model_name == 'DateTimeField':
                epoch = datetime.utcfromtimestamp(0)
                return (result.replace(tzinfo=None) -
                        epoch).total_seconds()
            if model_name == 'FileField':
                return result.name

        if hasattr(settings, 'METAMODEL'):
            ordering_valur_function_path = settings.METAMODEL.get(
                'ORDERING_FUNCTIONS', [])

            for path in ordering_valur_function_path:
                path_components = path.split('.')
                module = importlib.import_module(
                    '.'.join(path_components[:-1]))
                ordering_value_function = getattr(module, path_components[-1])
                result = ordering_value_function(self)
                if result:
                    return result

        if 'unicode' == self.model.ordering_field.strip():
            return self.unicode_representation
        ordering_field_names = \
            [field.strip() for field in self.model.ordering_field.split(',')]
        result = None
        for field_name in ordering_field_names:
            field_value = getattr(self, field_name)
            if isinstance(field_value, InstanceModel):
                # this can fail because Numbers can be so big
                field_ordering_value = field_value.compute_ordering_value()
            else:
                try:
                    field_instance_model = \
                        self.fields.get(field__name=field_name).value
                    field_ordering_value = \
                        field_instance_model.get_ordering_value()
                except InstanceField.DoesNotExist:
                    field_ordering_value = ''
                if isinstance(field_ordering_value, str):
                    len_field = len(field_ordering_value)
                    field_ordering_value = '{}'.format(
                            field_ordering_value+' '*(30-len_field))

            if result is None:
                result = field_ordering_value
                continue

            if type(result) == type(field_ordering_value):
                if isinstance(result, str):
                    result = '{0}{1}'.format(result, field_ordering_value)
                else:
                    result = result*10**15+field_ordering_value
            else:
                if isinstance(result, str):
                    field_ordering_value = '{:.0f}'.format(
                            (field_ordering_value*1000).quantize(0))
                    result = '{0}{1}{2}'.format(
                            result,
                            '0'*(15-len(field_ordering_value) % 15),
                            field_ordering_value)
                else:
                    result = '{0}{1}'.format(
                            str((result*1000).quantize(0)),
                            field_ordering_value)

        return result

    @classmethod
    def delete_non_used_primitives(cls):
        cls.objects.filter(model__in=MetaModel.get_primitive(),
                           fields_usage__isnull=True).delete()

    def clone(self, creator_id):
        from metamodel.models import InstanceField

        cloned_instance = InstanceModel()
        fields_to_clone = self.fields.select_related()
        cloned_instance.model = self.model
        cloned_instance.save(initial=True)

        new_instance_fields = []

        for instance_field_to_clone in fields_to_clone:
            atr_field_name = instance_field_to_clone.field.name
            new_instance_field = instance_field_to_clone.copy(cloned_instance)

            if atr_field_name == 'old_id':
                new_instance_field.value.decimal_value = Decimal('0')
                new_instance_field.value.save()
            new_instance_fields.append(new_instance_field)

        InstanceField.objects.bulk_create(new_instance_fields)

        for label_field in ['name', 'part_number']:
            try:
                original_value = getattr(cloned_instance, label_field)
                if original_value is None:
                    original_value = ''

                setattr(cloned_instance, label_field,
                        '{} (clone)'.format(original_value))

                break
            except KeyError:
                # IM does not have the given attribute
                pass

        cloned_instance.save(creator_id=creator_id)

        return cloned_instance

    def elasticsearch_document(self):
        """
        Generates the elasticsearch document of the given InstanceModel
        based on its fields and unicode representation and automatically
        following all of its relations.
        """

        def sanitize_value(value):
            serialized_value = value

            if type(value) == Decimal:
                serialized_value = float(value)

            if type(value) == FieldFile:
                serialized_value = value.name

            try:
                json.dumps(serialized_value)
                return serialized_value
            except TypeError:
                raise

        if not self:
            return {}, []

        result = {
            u'id': self.id,
            u'unicode': str(self)
        }

        keywords = result[u'unicode'].split()

        meta_fields = MetaModel.get_metafields_by_model_id(
            self.model_id)

        instance_fields = self.fields.select_related()

        instance_values_dict = {instance_field.field: instance_field.value
                                for instance_field in instance_fields}

        for meta_field in meta_fields:
            if meta_field.multiple:
                m2m_documents = []

                m2m_instance_fields = instance_fields.filter(
                    field=meta_field).select_related()

                if not m2m_instance_fields:
                    continue

                for m2m_instance_field in m2m_instance_fields:
                    m2m_document = m2m_instance_field.value\
                        .elasticsearch_document()

                    m2m_documents.append(m2m_document[0])
                    keywords.extend(m2m_document[1])

                keys = m2m_documents[0].keys()

                for key in keys:
                    key_subresult = [d[key] for d in m2m_documents]
                    result[meta_field.name + '_' + key] = key_subresult
            else:
                try:
                    instance_value = instance_values_dict[meta_field]
                except KeyError:
                    instance_value = None

                if meta_field.model.is_primitive():
                    value = instance_value
                    if value:
                        value = instance_value.value

                    sanitized_value = sanitize_value(value)
                    result[meta_field.name] = sanitized_value
                    keywords.append(str(sanitized_value))
                elif instance_value:
                    fk_result = instance_value.elasticsearch_document()
                    for fk_key, fk_value in fk_result[0].items():
                        try:
                            result[meta_field.name + '_' + fk_key] = \
                                sanitize_value(fk_value)
                        except TypeError:
                            pass

                    keywords.extend(fk_result[1])

        for function_path in settings.METAMODEL[
                'ADDITIONAL_ELASTICSEARCH_FIELDS_FUNCTIONS']:
            path_components = function_path.split('.')
            f_module = importlib.import_module('.'.join(path_components[:-1]))
            additional_es_fields_function = getattr(
                f_module, path_components[-1])
            additional_fields = \
                additional_es_fields_function(self, result)
            if additional_fields:
                result.update(additional_fields)

        return result, keywords

    class Meta:
        app_label = 'metamodel'
        ordering = ('decimal_value', 'unicode_value',
                    'unicode_representation')
