from django import forms

from solotodo.models import Category


class CategoryForm(forms.Form):
    category = forms.ModelChoiceField(queryset=Category.objects.all())
