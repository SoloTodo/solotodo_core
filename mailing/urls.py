from django.conf.urls import url
from django.views.generic import TemplateView

urlpatterns = [
    url('demo', TemplateView.as_view(template_name='mailing/index.html'))
]