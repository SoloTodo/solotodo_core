from django import forms


class EntityEstimatedSalesForm(forms.Form):
    timestamp_0 = forms.DateTimeField(required=False)
    timestamp_1 = forms.DateTimeField(required=False)
    limit = forms.IntegerField(required=False)
