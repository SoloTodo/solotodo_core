import csv
import io
from datetime import timedelta

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import models, connections
from django.db.models import Count
from django.db.models.functions import ExtractWeek, ExtractIsoYear
from django.utils import timezone
from django_redshift_backend.distkey import DistKey

from solotodo_core.s3utils import PrivateSaS3Boto3Storage


class LgRsBanner(models.Model):
    store_id = models.IntegerField()
    store_name = models.CharField(max_length=255)
    category_id = models.IntegerField()
    category_name = models.CharField(max_length=255)
    banner_id = models.IntegerField()
    asset_id = models.IntegerField()
    content_id = models.IntegerField()
    section_id = models.IntegerField()
    section_name = models.CharField(max_length=255)
    subsection_id = models.IntegerField()
    subsection_name = models.CharField(max_length=255)
    type_id = models.IntegerField()
    type_name = models.CharField(max_length=255)
    brand_id = models.IntegerField()
    brand_name = models.CharField(max_length=255)
    timestamp = models.DateTimeField()
    update_id = models.IntegerField()
    picture_url = models.URLField()
    banner_url = models.URLField()
    score = models.IntegerField()
    store_week_updates = models.IntegerField()
    normalized_score = models.FloatField()
    is_active = models.BooleanField()

    def str(self):
        return self.id

    @classmethod
    def synchronize_with_db_banners(cls, banners=None):
        from banners.models import Banner, BannerUpdate

        if not banners:
            banners = Banner.objects.filter(
                update__timestamp__gte=timezone.now() - timedelta(days=14)
            )

        banners = banners.annotate(
            week=ExtractWeek("update__timestamp"),
            year=ExtractIsoYear("update__timestamp"),
        ).select_related(
            "update__store", "subsection__section", "subsection__type", "asset"
        )

        banner_updates = (
            BannerUpdate.objects.annotate(
                week=ExtractWeek("timestamp"), year=ExtractIsoYear("timestamp")
            )
            .order_by("store", "year", "week")
            .values("store", "year", "week")
            .annotate(c=Count("*"))
        )

        updates_per_week = {
            (x["store"], x["year"], x["week"]): x["c"] for x in banner_updates
        }

        lines = []

        banner_count = banners.count()

        for idx, banner in enumerate(banners):
            print("Processing: {} / {}".format(idx + 1, banner_count))
            for content in banner.asset.contents.select_related("brand", "category"):
                update_count = updates_per_week[
                    (banner.update.store.id, banner.year, banner.week)
                ]

                lines.append(
                    [
                        banner.update.store.id,
                        str(banner.update.store),
                        content.category.id,
                        str(content.category),
                        banner.id,
                        banner.asset.id,
                        content.id,
                        banner.subsection.section.id,
                        str(banner.subsection.section),
                        banner.subsection.id,
                        str(banner.subsection),
                        banner.subsection.type.id,
                        str(banner.subsection.type),
                        content.brand.id,
                        str(content.brand),
                        str(banner.update.timestamp),
                        banner.update.id,
                        banner.asset.picture_url[:200],
                        banner.url,
                        content.percentage,
                        update_count,
                        content.percentage / update_count,
                        "t"
                        if banner.update.store.active_banner_update_id
                        == banner.update.id
                        else "f",
                    ]
                )

        print("Creating in memory CSV File")

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerows(lines)

        output.seek(0)
        file_for_upload = ContentFile(output.getvalue().encode("utf-8"))

        print("Uploading CSV file")

        storage = PrivateSaS3Boto3Storage()
        storage.file_overwrite = True
        path = "lg_pricing/banners.csv"
        storage.save(path, file_for_upload)

        print("Deleting existing banner data in Redshift")

        cls.objects.filter(banner_id__in=[x.id for x in banners]).delete()

        print("Loading new data into Redshift")

        cursor = connections["lg_pricing"].cursor()
        command = """
                copy {} from 's3://{}/{}'
                credentials 'aws_access_key_id={};aws_secret_access_key={}'
                csv;
                """.format(
            cls._meta.db_table,
            settings.AWS_SA_STORAGE_BUCKET_NAME,
            path,
            settings.AWS_ACCESS_KEY_ID,
            settings.AWS_SECRET_ACCESS_KEY,
        )

        cursor.execute(command)
        cursor.close()

    class Meta:
        app_label = "lg_pricing"
        indexes = [DistKey(fields=["brand_id"])]
        ordering = ("timestamp",)
