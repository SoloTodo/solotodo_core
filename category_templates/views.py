from django_filters import rest_framework
from rest_framework import viewsets, status
from rest_framework.decorators import detail_route
from rest_framework.response import Response

from category_templates.filters import CategoryTemplateFilterSet
from category_templates.models import CategoryTemplatePurpose, \
    CategoryTemplateTarget, CategoryTemplate
from category_templates.serializers import CategoryTemplatePurposeSerializer, \
    CategoryTemplateTargetSerializer, CategoryTemplateSerializer
from solotodo.forms.product_form import ProductForm


class CategoryTemplatePurposeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CategoryTemplatePurpose.objects.all()
    serializer_class = CategoryTemplatePurposeSerializer


class CategoryTemplateTargetViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CategoryTemplateTarget.objects.all()
    serializer_class = CategoryTemplateTargetSerializer


class CategoryTemplateViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CategoryTemplate.objects.all()
    serializer_class = CategoryTemplateSerializer
    filter_backends = (rest_framework.DjangoFilterBackend, )
    filter_class = CategoryTemplateFilterSet

    @detail_route()
    def render(self, request, pk, *args, **kwargs):
        category_template = self.get_object()
        form = ProductForm.from_user_and_category(
            request.user, category_template.category, request.query_params)

        if form.is_valid():
            response = {
                'body': category_template.render(form.cleaned_data['product'])
            }
            return Response(response)
        else:
            return Response({'detail': form.errors},
                            status.HTTP_400_BAD_REQUEST)
