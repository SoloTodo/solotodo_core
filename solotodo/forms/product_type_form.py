from django import forms

from solotodo.models import ProductType


class ProductTypeForm(forms.Form):
    product_type = forms.ModelChoiceField(queryset=ProductType.objects.all())
