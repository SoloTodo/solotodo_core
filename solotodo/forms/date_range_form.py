from django import forms
from django_filters.fields import IsoDateTimeRangeField


class DateRangeForm(forms.Form):
    timestamp = IsoDateTimeRangeField(required=False)
