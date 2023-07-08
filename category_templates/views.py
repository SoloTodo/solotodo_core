from django_filters import rest_framework
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from category_templates.filters import CategoryTemplateFilterSet
from category_templates.models import CategoryTemplatePurpose, \
    CategoryTemplate
from category_templates.serializers import CategoryTemplatePurposeSerializer, \
    CategoryTemplateSerializer
from solotodo.forms.product_form import ProductForm


class CategoryTemplatePurposeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CategoryTemplatePurpose.objects.all()
    serializer_class = CategoryTemplatePurposeSerializer


class CategoryTemplateViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CategoryTemplate.objects.all()
    serializer_class = CategoryTemplateSerializer
    filter_backends = (rest_framework.DjangoFilterBackend, )
    filterset_class = CategoryTemplateFilterSet

    @action(detail=True)
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
