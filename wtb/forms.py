from django import forms

from solotodo.models import Product


class WtbEntityAssociationForm(forms.Form):
    product = forms.ModelChoiceField(queryset=Product.objects.all())
