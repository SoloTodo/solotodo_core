from django import forms


class BudgetExportFormatForm(forms.Form):
    export_format = forms.ChoiceField(choices=[
        ('xls', 'Excel'),
        ('bbcode', 'BBCode'),
        ('img', 'Image'),
    ])
