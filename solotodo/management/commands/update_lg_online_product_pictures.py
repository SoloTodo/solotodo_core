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
            primary_picture_id = product_entry['main_picture_id']
            secondary_pictures_id = product_entry['secondary_pictures_id']

            product = Product.objects.get(pk=product_entry['productId'])
            print(product)

            os.mkdir('solotodo_core/tmp/')

            # Primary picture

            if primary_picture_id:
                primary_picture = drive.CreateFile({'id': primary_picture_id})
                primary_picture.GetContentFile('solotodo_core/tmp/' +
                                               primary_picture['title'])
            else:
                primary_picture = None

            # Secondary pictures

            if secondary_pictures_id:
                product.pictures.all().delete()

                file_list = drive.ListFile({
                    'q': "'{}' in parents".format(secondary_pictures_id)
                }).GetList()

                secondary_filenames = []

                file_list = sorted(file_list, key=lambda x: x['title'])[1:]

                for drive_file in file_list:
                    if drive_file['title'] == '.DS_Store':
                        continue

                    print('Downloading: {}'.format(drive_file['title']))
                    drive_file.GetContentFile('solotodo_core/tmp/' +
                                              drive_file['title'])

                    secondary_filenames.append(drive_file['title'])
            else:
                secondary_filenames = None

            time.sleep(2)

            subprocess.run(['mogrify', '-trim', '-fuzz', '5%', '-resize',
                            '1000x1000', 'solotodo_core/tmp/*.jpg'])

            # Upload primary picture

            if primary_picture:
                file_to_upload = open('solotodo_core/tmp/' +
                                      primary_picture['title'], 'rb')
                uploaded_file_path = storage.save(
                    'products/' + primary_picture['title'], file_to_upload)
                print(uploaded_file_path)
                product.instance_model.picture = uploaded_file_path
                product.instance_model.save()
                print('Uploaded: {}'.format(uploaded_file_path))
                file_to_upload.close()

            # Upload secondary pictures

            if secondary_filenames:
                for idx, filename in enumerate(secondary_filenames):
                    file_to_upload = open('solotodo_core/tmp/' + filename,
                                          'rb')
                    uploaded_file_path = storage.save(
                        'product_pictures/' + filename, file_to_upload)
                    ProductPicture.objects.create(
                        product=product,
                        file=uploaded_file_path,
                        ordering=idx+1
                    )
                    print('Uploaded: {}'.format(uploaded_file_path))
                    file_to_upload.close()

            shutil.rmtree('solotodo_core/tmp/')
