import csv
import io

from django.conf import settings
from django.contrib.auth.models import Group
from django.core.files.base import ContentFile
from django.db import models, connections
from django.db.models import Max, Avg
from django.db.models.functions import TruncDate
from django_redshift_backend.distkey import DistKey
from guardian.shortcuts import get_objects_for_group

from solotodo.models import Entity, StoreSection
from solotodo.utils import iterable_to_dict
from solotodo_core.s3utils import PrivateSaS3Boto3Storage


class LgRsEntitySectionPosition(models.Model):
    average_value = models.FloatField()
    section_id = models.IntegerField()
    section_name = models.CharField(max_length=256)
    store_id = models.IntegerField()
    store_name = models.CharField(max_length=256)
    date = models.DateField()
    entity_id = models.IntegerField()
    entity_name = models.CharField(max_length=256)
    category_id = models.IntegerField()
    category_name = models.CharField(max_length=256)
    product_id = models.IntegerField()
    product_name = models.CharField(max_length=256)
    brand_id = models.IntegerField()
    brand_name = models.CharField(max_length=256)
    sku = models.CharField(max_length=256, blank=True, null=True)
    url = models.URLField(max_length=512)

    def str(self):
        return self.id

    @classmethod
    def synchronize_with_db_positions(cls):
        from solotodo.models import Store, Category, EntitySectionPosition

        lg_group = Group.objects.get(pk=settings.LG_CHILE_GROUP_ID)

        stores = get_objects_for_group(lg_group, 'view_store', Store)
        categories = get_objects_for_group(lg_group, 'view_category', Category)

        positions_to_synchronize = EntitySectionPosition.objects.filter(
            entity_history__entity__store__in=stores,
            entity_history__entity__category__in=categories,
            entity_history__entity__product__isnull=False
        )

        last_synchronization = cls.objects.aggregate(Max('date'))['date__max']

        if last_synchronization:
            print('Synchronizing since {}'.format(last_synchronization))
            positions_to_synchronize = positions_to_synchronize.filter(
                entity_history__timestamp__gte=last_synchronization
            )
        else:
            print('Synchronizing from scratch')

        print('Obtaining data')

        aggregated_positions = positions_to_synchronize \
            .annotate(date=TruncDate('entity_history__timestamp'))\
            .order_by(
                'date',
                'entity_history__entity',
                'section')\
            .values(
                'date',
                'entity_history__entity',
                'section'
            ).annotate(avg_value=Avg('value'))

        entity_ids = set([x['entity_history__entity']
                          for x in aggregated_positions])
        entities = Entity.objects.filter(pk__in=entity_ids).select_related(
            'store',
            'category',
            'product__instance_model',
            'product__brand'
        )
        entities_dict = iterable_to_dict(entities)

        section_ids = set([x['section'] for x in aggregated_positions])
        sections = StoreSection.objects.filter(
            pk__in=section_ids).select_related('store')
        sections_dict = iterable_to_dict(sections)

        print('Creating in memory CSV File')
        output = io.StringIO()
        writer = csv.writer(output)
        data_count = len(aggregated_positions)

        for idx, entry in enumerate(aggregated_positions):
            print('Processing: {} / {}'.format(idx + 1, data_count))
            entity = entities_dict[entry['entity_history__entity']]
            section = sections_dict[entry['section']]

            writer.writerow([
                entry['avg_value'],
                section.id,
                str(section),
                entity.store.id,
                str(entity.store),
                entry['date'],
                entity.id,
                entity.name,
                entity.category.id,
                str(entity.category),
                entity.product.id,
                str(entity.product),
                entity.product.brand.id,
                str(entity.product.brand),
                entity.sku,
                entity.url
            ])

        output.seek(0)
        file_for_upload = ContentFile(output.getvalue().encode('utf-8'))

        print('Uploading CSV file')

        storage = PrivateSaS3Boto3Storage()
        storage.file_overwrite = True
        path = 'lg_pricing/entity_positions.csv'
        storage.save(path, file_for_upload)

        if last_synchronization:
            print('Deleting existing entity positions in Redshift')
            cls.objects.filter(date__gte=last_synchronization).delete()

        print('Loading new data into Redshift')

        cursor = connections['lg_pricing'].cursor()
        command = """
                    copy {} from 's3://{}/{}'
                    credentials 'aws_access_key_id={};aws_secret_access_key={}'
                    csv;
                    """.format(
            cls._meta.db_table,
            settings.AWS_SA_STORAGE_BUCKET_NAME,
            path,
            settings.AWS_ACCESS_KEY_ID,
            settings.AWS_SECRET_ACCESS_KEY
        )

        cursor.execute(command)
        cursor.close()

    class Meta:
        app_label = 'lg_pricing'
        indexes = [DistKey(fields=['brand_id'])]
        ordering = ['date']
