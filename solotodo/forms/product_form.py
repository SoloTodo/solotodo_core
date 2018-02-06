from django import forms

from solotodo.models import Product


class ProductForm(forms.Form):
    product = forms.ModelChoiceField(queryset=Product.objects.all())

    @classmethod
    def from_user_and_category(cls, user, category, data):
        form = cls(data)

        products = Product.objects\
            .filter_by_category(category)\
            .filter_by_user_perms(user, 'view_product')

        form.fields['product'].queryset = products
        return form

    @classmethod
    def from_user(cls, user, data):
        form = cls(data)

        products = Product.objects\
            .filter_by_user_perms(user, 'view_product')

        form.fields['product'].queryset = products
        return form
