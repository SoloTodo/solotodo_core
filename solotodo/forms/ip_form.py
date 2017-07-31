from django import forms


class IpForm(forms.Form):
    ip = forms.GenericIPAddressField()
