from django.db import models

from solotodo.models import Category


class CategoryTemplateTarget(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ('name', )


class CategoryTemplatePurpose(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ('name', )


class CategoryTemplate(models.Model):
    category = models.ForeignKey(Category)
    target = models.ForeignKey(CategoryTemplateTarget)
    purpose = models.ForeignKey(CategoryTemplatePurpose)
    body = models.TextField()

    def __str__(self):
        return '{} - {} - {}'.format(self.category, self.target, self.purpose)

    class Meta:
        ordering = ('category', 'target', 'purpose')
        unique_together = ('category', 'target', 'purpose')
