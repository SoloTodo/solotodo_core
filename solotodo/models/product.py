import collections

from django.contrib.auth import get_user_model
from django.db import models

from metamodel.models import InstanceModel


class ProductQuerySet(models.QuerySet):
    def filter_by_category(self, category):
        lookup = 'instance_model__model__category'
        if isinstance(category, collections.Iterable):
            lookup += '__in'

        return self.filter(**{lookup: category})


class Product(models.Model):
    instance_model = models.ForeignKey(InstanceModel)
    creation_date = models.DateTimeField(db_index=True, auto_now_add=True)
    creator = models.ForeignKey(get_user_model())

    objects = ProductQuerySet.as_manager()

    category = property(lambda self: self.instance_model.model.category)

    def __str__(self):
        return str(self.instance_model)

    def save(self, *args, **kwargs):
        from django.conf import settings

        super(Product, self).save(*args, **kwargs)

        es = settings.ES
        document, keywords = self.instance_model.elasticsearch_document()

        document[u'product_id'] = self.id
        document[u'keywords'] = ' '.join(keywords)

        es.index(index=settings.ES_INDEX,
                 doc_type=self.category.storescraper_name,
                 id=self.id,
                 body=document)

    class Meta:
        app_label = 'solotodo'
        ordering = ('instance_model', )
