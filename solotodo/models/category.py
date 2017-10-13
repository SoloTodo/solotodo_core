from django.conf import settings
from django.db import models
from elasticsearch_dsl import Search
from guardian.shortcuts import get_objects_for_user

from metamodel.models import MetaModel
from solotodo.forms.category_specs_form import CategorySpecsForm
from solotodo.models.category_tier import CategoryTier


class CategoryQuerySet(models.QuerySet):
    def filter_by_user_perms(self, user, permission):
        return get_objects_for_user(user, permission, self)


class Category(models.Model):
    name = models.CharField(max_length=255, db_index=True, unique=True)
    meta_model = models.OneToOneField(MetaModel, blank=True, null=True)
    tier = models.ForeignKey(CategoryTier, blank=True, null=True)
    slug = models.SlugField(blank=True, null=True)
    storescraper_name = models.CharField(
        max_length=255, db_index=True, blank=True, null=True)
    suggested_alternatives_ordering = models.CharField(
        max_length=255, blank=True, null=True)
    suggested_alternatives_filter = models.CharField(
        max_length=255, blank=True, null=True)
    similar_products_fields = models.CharField(
        max_length=255, null=True, blank=True)
    search_bucket_key_fields = models.CharField(
        max_length=255, null=True, blank=True)
    detail_bucket_key_fields = models.CharField(
        max_length=255, null=True, blank=True)

    objects = CategoryQuerySet.as_manager()

    def __str__(self):
        return self.name

    def es_search(self):
        return Search(using=settings.ES, index=settings.ES_PRODUCTS_INDEX,
                      doc_type=str(self.meta_model))

    def specs_form(self):
        form_class = type(
            '{}SpecsForm'.format(self.meta_model.name),
            (CategorySpecsForm,),
            {
                'category': self,
                'category_specs_filters': [],
                'ordering_value_to_es_field_dict': {}
            })

        for category_specs_order in self.categoryspecsfilter_set.\
                select_related('meta_model'):
            form_class.add_filter(category_specs_order)

        for category_specs_order in self.categoryspecsorder_set.all():
            form_class.add_order(category_specs_order)

        return form_class

    class Meta:
        app_label = 'solotodo'
        ordering = ['name']
        permissions = (
            ['view_category', 'Can view the category'],
            ['view_category_stocks', 'Can view the category entities stock '
                                     '(also requires store permissions)'],
            ['is_category_staff',
             'Is staff of the category (may also require other permissions)'],
            ['update_category_pricing',
             'Can update the pricing of the category\'s entities'],
            ['view_category_leads',
             'View the leads associated to this category'],
            ('backend_list_categories', 'View category list in backend')
        )
