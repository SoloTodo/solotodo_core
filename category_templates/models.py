from django.db import models
from django.template import Template, Context

from solotodo.models import Category, ApiClient


class CategoryTemplatePurpose(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ('name', )


class CategoryTemplate(models.Model):
    category = models.ForeignKey(Category)
    api_client = models.ForeignKey(ApiClient)
    purpose = models.ForeignKey(CategoryTemplatePurpose)
    body = models.TextField()

    def __str__(self):
        return '{} - {} - {}'.format(self.category, self.api_client,
                                     self.purpose)

    def render(self, product):
        template = Template(self.body)
        context = Context(product.specs)
        return template.render(context)

    class Meta:
        ordering = ('category', 'api_client', 'purpose')
        unique_together = ('category', 'api_client', 'purpose')
