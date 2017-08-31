from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError

from solotodo.models import Product


class EntityAssociationForm(forms.Form):
    product = forms.ModelChoiceField(queryset=Product.objects.all())
    cell_plan = forms.ModelChoiceField(
        queryset=Product.objects.filter_by_category(
            settings.CELL_PLAN_CATEGORY),
        required=False)

    def validate_for_entity(self, entity):
        product = self.cleaned_data['product']
        cell_plan = self.cleaned_data['cell_plan']

        if entity.category != product.category:
            raise ValidationError('The category of the product must be '
                                  'the same as the entity')
        if entity.product == product and entity.cell_plan == cell_plan:
            raise ValidationError('The new product / cell plan combination '
                                  'must be different from the old one')
