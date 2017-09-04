from django import forms

from solotodo.models import EntityState


class EntityStateForm(forms.Form):
    entity_state = forms.ModelChoiceField(queryset=EntityState.objects.all())
