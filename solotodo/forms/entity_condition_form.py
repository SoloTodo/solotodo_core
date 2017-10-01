from django import forms


class EntityConditionForm(forms.Form):
    condition = forms.ChoiceField(choices=[
        ('https://schema.org/DamagedCondition', 'Damaged'),
        ('https://schema.org/NewCondition', 'New'),
        ('https://schema.org/RefurbishedCondition', 'Refurbished'),
        ('https://schema.org/UsedCondition', 'Used')
    ])
