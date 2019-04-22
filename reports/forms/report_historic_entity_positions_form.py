from django import forms

from solotodo.filter_utils import IsoDateTimeRangeField
from solotodo.models import Category, Brand, Store


class ReportHistoricEntityPositionsForm(forms.Form):
    timestamp = IsoDateTimeRangeField()
    categories = forms.ModelMultipleChoiceField(
        queryset=Category.objects.all(),
        required=False
    )
    stores = forms.ModelMultipleChoiceField(
        queryset=Store.objects.all(),
        required=False
    )
    brands = forms.ModelMultipleChoiceField(
        queryset=Brand.objects.all(),
        required=False
    )
    position_threshold = forms.IntegerField(
        required=False
    )

    def generate_report(self):
        pass
