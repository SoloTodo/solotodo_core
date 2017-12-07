from django.conf import settings
from django.db import models, IntegrityError
from metamodel.models import InstanceModel, MetaField


class InstanceField(models.Model):
    parent = models.ForeignKey(InstanceModel, on_delete=models.CASCADE,
                               related_name='fields')
    field = models.ForeignKey(MetaField, on_delete=models.CASCADE)
    value = models.ForeignKey(InstanceModel, on_delete=models.CASCADE,
                              related_name='fields_usage')

    def __str__(self):
        return '{0} - {1}: {2}'.format(self.parent, self.field.name,
                                       self.value)

    def save(self, *args, **kwargs):
        if settings.METAMODEL['DEBUG']:
            if self.pk:
                existing_instance_field = InstanceField.objects.get(pk=self.pk)
                if existing_instance_field.parent != self.parent:
                    raise IntegrityError(
                        'Cannot change the parent of an existing '
                        'instance field')

                if existing_instance_field.field != self.field:
                    raise IntegrityError(
                        'Cannot change the meta field of an existing '
                        'instance field')

            if self.field.model != self.value.model:
                raise IntegrityError(
                    'Inconsistent model for field. MetaModel expected {0}, '
                    'given {1}'.format(self.field.model, self.value.model))

            if self.field.parent != self.parent.model:
                raise IntegrityError(
                    'Inconsistent model parent for field. MetaModel '
                    'expectd {0}, given {1}'.format(
                        self.field.parent, self.parent.model)
                )

            if not self.pk and not self.field.multiple:
                try:
                    InstanceField.objects.get(
                        parent=self.parent,
                        field=self.field
                    )

                    raise IntegrityError(
                        'There is already a field {0} for model {1}'.format(
                            self.parent, self.field))
                except InstanceField.DoesNotExist:
                    pass

        return super(InstanceField, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if settings.METAMODEL['DEBUG']:
            if not self.field.nullable and not self.field.multiple:
                raise IntegrityError('Cannot delete non-nullable field')

        if self.field.model.is_primitive():
            self.value.delete()

        super(InstanceField, self).delete(*args, **kwargs)

    @classmethod
    def get_or_create_with_value(cls, parent, field, value):
        from metamodel.models import MetaModel

        primitive_models_dict = MetaModel.get_primitive_models_dict()

        if field.multiple:
            raise Exception('This method is only consistent for '
                            'non-multiple fields')

        try:
            instance_field = cls.objects.get(parent=parent, field=field)

            if value is None or value == '':
                instance_field.delete()
                return None

            if field.model_id in primitive_models_dict:
                instance_field.value.value = value
                instance_field.value.save()
                return instance_field

        except cls.DoesNotExist:
            if value is None or value == '':
                return

            instance_field = InstanceField(parent=parent, field=field)

            if field.model_id in primitive_models_dict:
                instance_value = InstanceModel(model=field.model)
                instance_value.value = value
                instance_value.save()
                value = instance_value

        instance_field.value = value
        instance_field.save()

        return instance_field

    def copy(self, parent):
        new_field = InstanceField()
        new_field.parent = parent
        new_field.field = self.field

        model_value = self.value

        if model_value.model.is_primitive():
            new_field_value = InstanceModel()
            new_field_value.model = model_value.model
            new_field_value.decimal_value = model_value.decimal_value
            new_field_value.unicode_value = model_value.unicode_value
            new_field_value.unicode_representation = \
                model_value.unicode_representation
            new_field_value.save()
            new_field.value = new_field_value
        else:
            new_field.value = model_value
        return new_field

    class Meta:
        app_label = 'metamodel'
        ordering = ('parent', 'field', 'value')
