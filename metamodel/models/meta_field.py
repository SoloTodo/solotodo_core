from decimal import Decimal
import keyword
from datetime import datetime
from django.db import models, IntegrityError
from django import forms
from django.urls import reverse

from metamodel.models.meta_model import MetaModel
import re


class MetaField(models.Model):
    name = models.CharField(max_length=100)
    parent = models.ForeignKey(
        MetaModel, on_delete=models.CASCADE, related_name="fields"
    )
    nullable = models.BooleanField(default=False)
    multiple = models.BooleanField(default=False)
    model = models.ForeignKey(
        MetaModel, on_delete=models.CASCADE, related_name="fields_usage"
    )
    ordering = models.IntegerField(default=1)
    hidden = models.BooleanField(default=False)
    help_text = models.TextField(null=True, blank=True)

    MODEL_ID_FIELD_CLASS_DICT = None

    def __str__(self):
        return "{} - {} ({})".format(self.parent, self.name, self.model)

    def requires_default_value_for_saving(self):
        if self.nullable or self.multiple:
            return False

        if not self.parent.instancemodel_set.all():
            return False

        return True

    def clean_value(self, value):
        from metamodel.models import InstanceModel

        mtype = self.model.name

        if mtype == "BooleanField":
            return bool(value)

        if mtype == "CharField":
            if not value:
                return None

            return value

        if mtype == "DateField":
            return datetime.strptime(value, "%Y-%m-%d").date()

        if mtype == "DateTimeField":
            return datetime.strptime(value, "%Y-%m-%dT%H:%M")

        if mtype == "DecimalField":
            return Decimal(value)

        if mtype == "FileField":
            if not value:
                return None

            return value

        if mtype == "IntegerField":
            return int(value)

        return InstanceModel.objects.get(pk=value)

    def is_model_primitive(self):
        primitive_models_dict = MetaModel.get_primitive_models_dict()
        return self.model_id in primitive_models_dict

    def get_form_field(self):
        class MetaSelect(forms.Select):
            def __init__(self, meta_field, attrs=None, choices=()):
                self.meta_field = meta_field
                super(MetaSelect, self).__init__(attrs=attrs, choices=choices)

            def render(self, name, value, attrs=None, renderer=None):
                real_attrs = attrs
                if real_attrs is None:
                    real_attrs = {}

                real_attrs["class"] = "form-control"

                result = super(MetaSelect, self).render(
                    name, value, real_attrs, renderer
                )

                url = (
                    reverse(
                        "metamodel_model_add_instance",
                        kwargs={"pk": self.meta_field.model.id},
                    )
                    + "?popup=1"
                )

                result += (
                    ' <a href="{}" data-model="{}" '
                    'class="add_new_link" tabindex="-1">Add new</a>'
                    "".format(url, self.meta_field.model.id)
                )

                return result

        class MetaSelectMultiple(forms.SelectMultiple):
            def __init__(self, meta_field, attrs=None, choices=()):
                if attrs is None:
                    attrs = {}

                attrs["size"] = 10
                attrs["class"] = "form-control"

                self.meta_field = meta_field
                super(MetaSelectMultiple, self).__init__(attrs=attrs, choices=choices)

            def render(self, name, value, attrs=None, renderer=None):
                result = super(MetaSelectMultiple, self).render(
                    name, value, attrs, renderer
                )

                url = (
                    reverse(
                        "metamodel_model_add_instance",
                        kwargs={"pk": self.meta_field.model.id},
                    )
                    + "?popup=1"
                )

                result += (
                    ' <a href="{}" data-model="{}" '
                    'class="add_new_link" tabindex="-1">Add new</a>'
                    "".format(url, self.meta_field.model.id)
                )

                return result

        if self.is_model_primitive():
            model_name, field_klass = self.get_field_by_model_id()
            widget = MetaModel.NAME_INPUT_TYPES_DICT[model_name][1]

            kwargs = {"required": not self.nullable}

            if self.help_text:
                kwargs["help_text"] = self.help_text

            if model_name == "BooleanField":
                if self.nullable:
                    field_klass = forms.NullBooleanField

            if field_klass == forms.BooleanField:
                kwargs["required"] = False

            if field_klass == forms.DateTimeField:
                kwargs["input_formats"] = ["%Y-%m-%dT%H:%M"]

            if field_klass == forms.DateField:
                kwargs["input_formats"] = ["%Y-%m-%d"]

            if widget:
                kwargs["widget"] = widget

            return field_klass(**kwargs)
        else:
            if self.multiple:
                return forms.ModelMultipleChoiceField(
                    queryset=self.model.instancemodel_set.all(),
                    required=not self.nullable,
                    widget=MetaSelectMultiple(self),
                    help_text=self.help_text,
                )
            else:
                return forms.ModelChoiceField(
                    queryset=self.model.instancemodel_set.all(),
                    required=not self.nullable,
                    widget=MetaSelect(self),
                    help_text=self.help_text,
                )

    def save(self, *args, **kwargs):
        from metamodel.models import InstanceField, InstanceModel

        if keyword.iskeyword(self.name):
            raise IntegrityError("Chosen name is a keyword")

        if not re.match(r"[_A-Za-z][_a-zA-Z0-9]*$", self.name):
            raise IntegrityError("Please choose a valid Python identifier")

        default = kwargs.pop("default", None)

        def create_necessary_instance_fields():
            if isinstance(default, InstanceModel) and default.model != self.model:
                raise IntegrityError(
                    "Expected default of type {}, given {}".format(
                        self.model, default.model
                    )
                )

            super(MetaField, self).save(*args, **kwargs)

            for instance_model in self.parent.instancemodel_set.all():
                if not self.is_model_primitive():
                    default_value = default
                else:
                    # Primitive values have to be copied so that they only
                    # belong to exactly one model entity
                    default_value = InstanceModel(model=self.model)
                    default_value.value = default
                    default_value.save()

                try:
                    InstanceField.objects.get(parent=instance_model, field=self)
                except InstanceField.DoesNotExist:
                    InstanceField.objects.create(
                        parent=instance_model, field=self, value=default_value
                    )

            return

        if self.hidden and not self.nullable and not self.multiple:
            raise IntegrityError("Hidden fields must be either nullable " "or multiple")

        if self.pk:
            # Already in the dabase, has it changed?
            old_field = MetaField.objects.get(pk=self.pk)

            if old_field.model != self.model:
                raise IntegrityError("Can't change model after creating " "the field")

            if old_field.parent != self.parent:
                raise IntegrityError("Can't change parent after creating " "the field")
            if old_field.multiple and not self.multiple:
                raise IntegrityError(
                    "Can't change field from multiple to " "non-multiple"
                )
            if (
                not old_field.requires_default_value_for_saving()
                and self.requires_default_value_for_saving()
            ):
                if default is None:
                    raise IntegrityError(
                        "Changing field from null to non-null should include "
                        "a default value for existing entries"
                    )
                else:
                    return create_necessary_instance_fields()
            else:
                if default:
                    raise IntegrityError("Default value is not needed")

        else:
            if self.requires_default_value_for_saving() and default is None:
                raise IntegrityError(
                    "New non-nullable non-multiple fields "
                    "must provide a default for "
                    "auto-created rows"
                )

            if not self.requires_default_value_for_saving() and default is not None:
                raise IntegrityError("Default value is not needed")

            if default:
                return create_necessary_instance_fields()

        super(MetaField, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.is_model_primitive():
            for field in self.instancefield_set.all():
                field.value.delete()

        super(MetaField, self).delete(*args, **kwargs)

    def get_field_by_model_id(self):
        def refresh_dict():
            self.MODEL_ID_FIELD_CLASS_DICT = {
                m.id: (m.name, getattr(forms, m.name))
                for m in MetaModel.get_primitive()
            }

        if self.MODEL_ID_FIELD_CLASS_DICT is None:
            refresh_dict()

        field = self.MODEL_ID_FIELD_CLASS_DICT.get(self.model_id, None)
        if not field:
            refresh_dict()
        return self.MODEL_ID_FIELD_CLASS_DICT[self.model_id]

    class Meta:
        app_label = "metamodel"
        unique_together = ("parent", "name")
        ordering = ("parent", "ordering", "pk")
