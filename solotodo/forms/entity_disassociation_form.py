from django import forms
from django.conf import settings

from solotodo.models import Product


class EntityDisssociationForm(forms.Form):
    reason = forms.CharField(required=False)
