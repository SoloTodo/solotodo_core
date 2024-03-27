import csv
import io

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import models, connections
from django.db.models import Max
from django_redshift_backend import DistKey

from solotodo_core.s3utils import PrivateSaS3Boto3Storage


class LgRsProduct(models.Model):
    product_id = models.IntegerField()
    product_name = models.CharField(max_length=255)
    category_id = models.IntegerField()
    category_name = models.CharField(max_length=255)
    brand_id = models.IntegerField()
    brand_name = models.CharField(max_length=255)
    creation_date = models.DateTimeField()
    last_updated = models.DateTimeField()
    spec_num_1 = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    spec_num_2 = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    spec_num_3 = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    spec_num_4 = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    spec_num_5 = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    spec_txt_1 = models.CharField(max_length=256, null=True, blank=True)
    spec_txt_2 = models.CharField(max_length=256, null=True, blank=True)
    spec_txt_3 = models.CharField(max_length=256, null=True, blank=True)
    spec_txt_4 = models.CharField(max_length=256, null=True, blank=True)
    spec_txt_5 = models.CharField(max_length=256, null=True, blank=True)

    category_specs_dict = {
        11: (
            ["size_family_value"],
            [
                "display_unicode",
                "size_unicode",
                "resolution_unicode",
                "energy_efficiency_unicode",
            ],
        )
    }

    def str(self):
        return "{} - {}".format(self.id, self.name)

    @classmethod
    def synchronize_with_db_products(cls):
        from solotodo.models import Product

        valid_category_ids = cls.category_specs_dict.keys()
        products_to_synchronize = Product.objects.select_related(
            "instance_model__model__category", "brand"
        ).filter_by_category(valid_category_ids)
        last_synchronization = cls.objects.aggregate(Max("last_updated"))[
            "last_updated__max"
        ]

        if last_synchronization:
            print("Synchronizing since {}".format(last_synchronization))
            products_to_synchronize = products_to_synchronize.filter(
                lart_updated__gte=last_synchronization
            )
        else:
            print("Synchronizing from scratch")

        Product.prefetch_specs(products_to_synchronize)

        print("Obtaining data")
        print("Creating in memory CSV File")
        output = io.StringIO()
        writer = csv.writer(output)
        data_count = len(products_to_synchronize)

        for idx, product in enumerate(products_to_synchronize):
            print("Processing: {} / {}".format(idx + 1, data_count))

            num_spec_fields, txt_spec_fields = cls.category_specs_dict[
                product.category.id
            ]
            num_specs = [None] * 5
            txt_specs = [None] * 5

            for i, num_spec_field in enumerate(num_spec_fields):
                num_specs[i] = product.specs.get(num_spec_field, None)

            for i, txt_spec_field in enumerate(txt_spec_fields):
                txt_specs[i] = product.specs.get(txt_spec_field, None)

            specs = num_specs + txt_specs
            writer.writerow(
                [
                    product.id,
                    product.id,
                    str(product),
                    product.category.id,
                    str(product.category),
                    product.brand.id,
                    str(product.brand),
                    product.creation_date.isoformat(),
                    product.last_updated.isoformat(),
                    *specs,
                ]
            )

        output.seek(0)
        file_for_upload = ContentFile(output.getvalue().encode("utf-8"))

        print("Uploading CSV file")

        storage = PrivateSaS3Boto3Storage()
        storage.file_overwrite = True
        path = "lg_pricing/products.csv"
        storage.save(path, file_for_upload)

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
        indexes = [DistKey(fields=["product_id"])]
        ordering = ["last_updated"]
