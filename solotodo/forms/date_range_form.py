from django import forms

from solotodo.filter_utils import IsoDateTimeRangeField


class DateRangeForm(forms.Form):
    timestamp = IsoDateTimeRangeField(required=False)
