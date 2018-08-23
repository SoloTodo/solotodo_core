from django import forms
from django.core import signing


class AlertDeleteByKeyForm(forms.Form):
    payload = forms.CharField(max_length=255)

    def clean_payload(self):
        try:
            payload = signing.loads(self.cleaned_data['payload'])
        except signing.BadSignature:
            raise forms.ValidationError('Invalid payload')

        return payload
