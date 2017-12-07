from django.db import models
from django.template import Template, Context

from solotodo.models import Category, Website


class CategoryTemplatePurpose(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ('name', )


class CategoryTemplate(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    website = models.ForeignKey(Website, on_delete=models.CASCADE)
    purpose = models.ForeignKey(CategoryTemplatePurpose,
                                on_delete=models.CASCADE)
    body = models.TextField()

    def __str__(self):
        return '{} - {} - {}'.format(self.category, self.website,
                                     self.purpose)

    def render(self, product):
        template = Template(self.body)
        context = Context(product.specs)
        return template.render(context)

    class Meta:
        ordering = ('category', 'website', 'purpose')
        unique_together = ('category', 'website', 'purpose')
