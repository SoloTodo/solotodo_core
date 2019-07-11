import csv
import io

from django.contrib.auth.models import Group
from django.core.files.base import ContentFile
from django.db import models, connections
from django.db.models import Max, F
from django_redshift_backend.distkey import DistKey
from guardian.shortcuts import get_objects_for_group

from solotodo_core.s3utils import PrivateSaS3Boto3Storage


class LgRsEntityHistory(models.Model):
    entity_history_id = models.IntegerField()
    entity_id = models.IntegerField()
    timestamp = models.DateTimeField()
    normal_price = models.DecimalField(decimal_places=2, max_digits=12)
    offer_price = models.DecimalField(decimal_places=2, max_digits=12)
    picture_count = models.IntegerField(null=True, blank=True)
    video_count = models.IntegerField(null=True, blank=True)
    review_count = models.IntegerField(null=True, blank=True)
    review_avg_score = models.FloatField(null=True, blank=True)
    store_id = models.IntegerField()
    store_name = models.CharField(max_length=256)
    category_id = models.IntegerField()
    category_name = models.CharField(max_length=256)
    product_id = models.IntegerField()
    product_name = models.CharField(max_length=256)
    brand_id = models.IntegerField()
    brand_name = models.CharField(max_length=256)
    is_active = models.BooleanField()
    sku = models.CharField(max_length=256, blank=True, null=True)
    sku_url = models.URLField(max_length=512)
    sku_name = models.CharField(max_length=256, blank=True, null=True)
    cell_plan_id = models.IntegerField(blank=True, null=True)
    cell_plan_name = models.CharField(blank=True, null=True, max_length=256)

    def str(self):
        return self.id

    @classmethod
    def synchronize_with_db_entity_histories(cls):
        from solotodo.models import Store, Category, EntityHistory
        from django.conf import settings

        print('Getting old histories marked as active')
        active_histories_in_rs = cls.objects.filter(is_active=True)
        active_history_ids = [x.entity_history_id
                              for x in active_histories_in_rs]
        print('Found {} active entries in Redshift'.format(
            len(active_history_ids)))

        print('Obtaining updated data for those entries')
        inactive_entities = EntityHistory.objects.filter(
            pk__in=active_history_ids
        ).exclude(entity__active_registry_id=F('id'))
        inactive_entity_ids = [x.id for x in inactive_entities]
        print('Setting {} entries as inactive'.format(
            len(inactive_entity_ids)))
        rs_entries_to_be_updated = cls.objects.filter(
            entity_history_id__in=inactive_entity_ids)
        rs_entries_to_be_updated.update(is_active=False)

        print('Getting new data')
        lg_group = Group.objects.get(pk=settings.LG_CHILE_GROUP_ID)

        stores = get_objects_for_group(lg_group, 'view_store', Store)
        categories = get_objects_for_group(lg_group, 'view_category', Category)

        histories_to_synchronize = EntityHistory.objects.filter(
            cell_monthly_payment__isnull=True,
            entity__store__in=stores,
            entity__category__in=categories,
            entity__product__isnull=False,
        ).get_available().select_related(
            'entity__category',
            'entity__store',
            'entity__product__instance_model',
            'entity__product__brand'
        ).order_by('timestamp')

        last_synchronization = cls.objects.aggregate(Max(
            'timestamp'))['timestamp__max']

        if last_synchronization:
            print('Synchronizing since {}'.format(last_synchronization))
            histories_to_synchronize = histories_to_synchronize.filter(
                timestamp__gt=last_synchronization
            )
        else:
            print('Synchronizing from scratch')

        print('Creating in memory CSV File')
        output = io.StringIO()
        writer = csv.writer(output)

        print('Obtaining data')

        for idx, entity_history in enumerate(histories_to_synchronize):
            print('Processing: {}'.format(idx))

            if entity_history.entity.cell_plan:
                cell_plan_name = str(entity_history.entity.cell_plan)
            else:
                cell_plan_name = None

            writer.row([
                entity_history.id,
                entity_history.entity.id,
                entity_history.timestamp,
                entity_history.normal_price,
                entity_history.offer_price,
                entity_history.picture_count,
                entity_history.video_count,
                entity_history.review_count,
                entity_history.review_avg_score,
                entity_history.entity.store.id,
                str(entity_history.entity.store),
                entity_history.entity.category.id,
                str(entity_history.entity.category),
                entity_history.entity.product.id,
                str(entity_history.entity.product),
                entity_history.entity.product.brand.id,
                str(entity_history.entity.product.brand),
                entity_history.entity.active_registry_id ==
                entity_history.id,
                entity_history.entity.sku,
                entity_history.entity.url,
                entity_history.entity.name,
                entity_history.entity.cell_plan_id,
                cell_plan_name,
            ])

        print('Uploading CSV file')
        output.seek(0)
        file_for_upload = ContentFile(output.getvalue().encode('utf-8'))
        storage = PrivateSaS3Boto3Storage()
        storage.file_overwrite = True
        path = 'lg_pricing/entity_positions.csv'
        storage.save(path, file_for_upload)

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
        indexes = [DistKey(fields=['product_id'])]
        ordering = ['timestamp']
