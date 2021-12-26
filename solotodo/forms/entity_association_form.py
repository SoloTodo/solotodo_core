from django import forms
from django.conf import settings

from solotodo.models import Product, Bundle


class EntityAssociationForm(forms.Form):
    product = forms.ModelChoiceField(queryset=Product.objects.all())
    cell_plan = forms.ModelChoiceField(
        queryset=Product.objects.filter_by_category(
            settings.CELL_PLAN_CATEGORY),
        required=False)
    bundle = forms.ModelChoiceField(queryset=Bundle.objects.all(),
                                    required=False)
