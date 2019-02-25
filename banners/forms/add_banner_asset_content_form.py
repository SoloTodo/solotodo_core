from django import forms
from django.core.exceptions import ValidationError

from banners.models import BannerAssetContent
from solotodo.models import Brand, Category


class AddBannerAssetContentForm(forms.Form):
    brand = forms.ModelChoiceField(
        queryset=Brand.objects.all())
    category = forms.ModelChoiceField(
        queryset=Category.objects.all())
    percentage = forms.IntegerField(min_value=1, max_value=100)

    def add_content(self, banner_asset):
        brand = self.cleaned_data['brand']
        category = self.cleaned_data['category']
        percentage = self.cleaned_data['percentage']

        current_percentage = banner_asset.total_percentage or 0

        final_percentage = current_percentage + percentage

        if final_percentage > 100:
            raise ValidationError('Percentage sum is more than 100')

        BannerAssetContent.objects.create(
            asset=banner_asset,
            brand=brand,
            category=category,
            percentage=percentage)
