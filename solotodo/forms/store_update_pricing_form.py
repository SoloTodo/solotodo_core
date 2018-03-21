from django import forms
from guardian.shortcuts import get_objects_for_user

from solotodo.models import Category


class StoreUpdatePricingForm(forms.Form):
    discover_urls_concurrency = forms.IntegerField(
        min_value=1,
        max_value=10,
        required=False
    )
    products_for_url_concurrency = forms.IntegerField(
        min_value=1,
        max_value=20,
        required=False
    )
    async = forms.NullBooleanField()
    categories = forms.ModelMultipleChoiceField(
        queryset=Category.objects.none(),
        required=False
    )

    @classmethod
    def from_store_and_user(cls, store, user, data):
        valid_categories = get_objects_for_user(
            user, 'update_category_pricing',
            store.scraper_categories())

        form = cls(data)
        form.fields['categories'].queryset = valid_categories

        return form

    def default_categories(self):
        return self.fields['categories'].queryset
