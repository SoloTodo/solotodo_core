from django import forms

from guardian.shortcuts import get_objects_for_user

from solotodo.filter_utils import IsoDateTimeRangeField
from solotodo.models import Website, Store, Category


class ReportSoicosConversions(forms.Form):
    timestamp = IsoDateTimeRangeField()
    sites = forms.ModelMultipleChoiceField(
        queryset=Website.objects.all)
    stores = forms.ModelMultipleChoiceField(
        queryset=Store.objects.all())
    categories = forms.ModelMultipleChoiceField(
        queryset=Category.objects.all)

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        valid_categories = get_objects_for_user(user, 'view_category_reports',
                                                Category)
        self.fields['categories'].queryset = valid_categories

        valid_stores = get_objects_for_user(user, 'view_store_reports', Store)
        self.fields['stores'].queryset = valid_stores

    def clean_stores(self):
        selected_stores = self.cleaned_data['stores']
        if selected_stores:
            return selected_stores
        else:
            return self.fields['stores'].queryset

    def clean_categories(self):
        selected_categories = self.cleaned_data['categories']
        if selected_categories:
            return selected_categories
        else:
            return self.fields['categories'].queryset

    def clean_sites(self):
        selected_sites = self.cleaned_data['sites']
        if selected_sites:
            return selected_sites
        else:
            return self.fields['sites'].queryset

    def generate_report(self):
        categories = self.cleaned_data['categories']
        sites = self.cleaned_data['sites']
        stores = self.cleaned_data['stores']
        timestamp = self.cleaned_data['timestamp']

        import ipdb
        ipdb.set_trace()
