from django import forms


class ProductPictureForm(forms.Form):
    width = forms.IntegerField(min_value=1)
    height = forms.IntegerField(min_value=1)
    image_format = forms.ChoiceField(choices=[
        ('JPEG', 'JPEG image'),
        ('PNG', 'PNG image')
    ], required=False)
    quality = forms.IntegerField(min_value=1, max_value=100, required=False)

    def thumbnail_kwargs(self):
        data = self.cleaned_data

        result = {
            'geometry_string': '{}x{}'.format(data['width'], data['height'])
        }

        if data['image_format']:
            result['format'] = data['image_format']

        if data['quality']:
            result['quality'] = data['quality']

        return result
