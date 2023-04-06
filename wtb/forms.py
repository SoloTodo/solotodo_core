from django import forms

from solotodo.models import Product
from wtb.models import WtbBrand


class WtbEntityAssociationForm(forms.Form):
    product = forms.ModelChoiceField(queryset=Product.objects.all())


class WtbBrandForm(forms.Form):
    wtb_brand = forms.ModelChoiceField(queryset=WtbBrand.objects.all(),
                                       required=False)
