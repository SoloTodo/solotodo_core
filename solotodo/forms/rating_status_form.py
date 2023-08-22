from django.forms import ModelForm

from solotodo.models import Rating


class RatingStatusForm(ModelForm):
    class Meta:
        model = Rating
        fields = ['status']
