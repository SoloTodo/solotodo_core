from django_filters import rest_framework

from category_templates.models import CategoryTemplate
from solotodo.filter_querysets import categories__view
from solotodo.models import Category


class CategoryTemplateFilterSet(rest_framework.FilterSet):
    @property
    def qs(self):
        parent = super(CategoryTemplateFilterSet, self).qs
        if self.request:
            parent = parent.filter(
                category__in=Category.objects.filter_by_user_perms(
                    self.request.user))

        return parent

    class Meta:
        model = CategoryTemplate
        fields = ('category', 'purpose', 'target')
