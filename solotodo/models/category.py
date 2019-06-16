from django.conf import settings
from django.db import models
from elasticsearch_dsl import Search
from guardian.shortcuts import get_objects_for_user

from metamodel.models import MetaModel
from solotodo.forms.category_specs_form import CategorySpecsForm
from solotodo.forms.es_category_specs_form import EsCategorySpecsForm
from solotodo.models.category_tier import CategoryTier
from solotodo.models.utils import rs_refresh_model


class CategoryQuerySet(models.QuerySet):
    def filter_by_user_perms(self, user, permission):
        return get_objects_for_user(user, permission, self)


class Category(models.Model):
    name = models.CharField(max_length=255, db_index=True, unique=True)
    meta_model = models.OneToOneField(MetaModel, on_delete=models.CASCADE,
                                      blank=True, null=True)
    tier = models.ForeignKey(CategoryTier, on_delete=models.CASCADE,
                             blank=True, null=True)
    slug = models.SlugField(blank=True, null=True)
    storescraper_name = models.CharField(
        max_length=255, db_index=True, blank=True, null=True)
    budget_ordering = models.IntegerField(null=True, blank=True)
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
        return Search(index='products'
                      ).filter('term', category_id=self.id)

    def specs_form(self, form_type='db'):
        # TODO Remove DB form type once browse code path is eliminated

        if form_type == 'db':
            base_class = CategorySpecsForm
            prefix = 'DB'
        elif form_type == 'es':
            base_class = EsCategorySpecsForm
            prefix = 'ES'
        else:
            raise Exception('Invalid form type')

        form_class = type(
            '{}{}SpecsForm'.format(self.meta_model.name, prefix),
            (base_class,),
            {
                'category': self,
                'category_specs_filters': [],
                'ordering_value_to_es_field_dict': {}
            })

        for category_specs_filter in self.categoryspecsfilter_set.\
                select_related('meta_model'):
            form_class.add_filter(category_specs_filter)

        for category_specs_order in self.categoryspecsorder_set.all():
            form_class.add_order(category_specs_order)

        return form_class

    @classmethod
    def rs_refresh(cls):
        rs_refresh_model(cls, 'category', ['id', 'name'])

    class Meta:
        app_label = 'solotodo'
        ordering = ['name']
        permissions = (
            ['view_category', 'Can view the category'],
            ['is_category_staff', 'Is staff of the category'],
            ['view_category_leads',
             'View the leads associated to this category'],
            ['view_category_visits',
             'View the visits associated to this category'],
            ['view_category_reports',
             'Download the reports associated to this category'],
            ['view_category_share_of_shelves',
             'View share of shelves of the category'],
            ['create_category_product_list',
             'Can create a product list in this category'],
            ['create_category_brand_comparison',
             'Can create a brand comparison for this category'],
            ['backend_list_categories', 'View category list in backend'],
            ['view_category_entity_positions',
             'Can view category entity positions'],
            ['create_category_keyword_search',
             'Can create keyword searches in this category']
        )
