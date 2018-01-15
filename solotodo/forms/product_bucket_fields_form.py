from django import forms


class ProductBucketFieldForm(forms.Form):
    fields = forms.CharField(max_length=255)
