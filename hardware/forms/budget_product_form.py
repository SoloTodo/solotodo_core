from django import forms

from solotodo.models import Product


class BudgetProductForm(forms.Form):
    product = forms.ModelChoiceField(
        queryset=Product.objects.all()
    )

    @classmethod
    def from_budget(cls, budget, data):
        form = cls(data)
        form.fields['product'].queryset = budget.products_pool.all()
        return form
