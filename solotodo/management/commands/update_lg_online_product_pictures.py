import json
import subprocess
import time
import shutil
import os

from django.core.management import BaseCommand

from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive

from solotodo.models import Product, ProductPicture
from solotodo_core.s3utils import MediaRootS3Boto3Storage


class Command(BaseCommand):
    def handle(self, *args, **options):
        f = open('lg_online_products.json')
        product_entries = json.loads(f.read())
        f.close()

        gauth = GoogleAuth()
        gauth.CommandLineAuth()
        drive = GoogleDrive(gauth)

        storage = MediaRootS3Boto3Storage(upload_to='product_pictures')

        for product_idx, product_entry in enumerate(product_entries):
            print('Processing: {} / {}'.format(product_idx + 1,
                                               len(product_entries)))
            secondary_pictures_id = product_entry['secondary_pictures_id']
            if not secondary_pictures_id:
                continue

            product = Product.objects.get(pk=product_entry['productId'])
            print(product)

            product.pictures.all().delete()

            file_list = drive.ListFile({
                'q': "'{}' in parents".format(secondary_pictures_id)
            }).GetList()

            filenames = []

            file_list = sorted(file_list, key=lambda x: x['title'])[1:]

            os.mkdir('solotodo_core/tmp/')

            for drive_file in file_list:
                if drive_file['title'] == '.DS_Store':
                    continue

                print('Downloading: {}'.format(drive_file['title']))
                drive_file.GetContentFile('solotodo_core/tmp/' +
                                          drive_file['title'])

                filenames.append(drive_file['title'])

            time.sleep(2)

            subprocess.run(['mogrify', '-trim', '-fuzz', '5%', '-resize',
                            '1000x1000', 'solotodo_core/tmp/*.jpg'])

            for idx, filename in enumerate(filenames):
                file_to_upload = open('solotodo_core/tmp/' + filename, 'rb')
                uploaded_file_path = storage.save(
                    'product_pictures/' + filename, file_to_upload)
                ProductPicture.objects.create(
                    product=product,
                    file=uploaded_file_path,
                    ordering=idx+1
                )
                print('Uploaded: {}'.format(uploaded_file_path))

            shutil.rmtree('solotodo_core/tmp/')
