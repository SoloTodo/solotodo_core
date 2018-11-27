import json
import re
import subprocess
import time
import shutil
import os

from django.core.management import BaseCommand

from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive

from solotodo.models import Product, ProductPicture
from solotodo_core.s3utils import MediaRootS3Boto3Storage


def normalize_filename(filename):
    return re.sub(r'([_|\-])(\d)\.(jpg|png)$',
                  r'\g<1>0\g<2>.\g<3>',
                  filename)


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
            primary_picture_id = product_entry['mainPictureId']
            secondary_pictures_id = product_entry['secondaryPicturesId']

            product = Product.objects.get(pk=product_entry['productId'])
            print(product)

            os.mkdir('solotodo_core/tmp/')

            # Secondary pictures

            if secondary_pictures_id:
                product.pictures.all().delete()

                file_list = drive.ListFile({
                    'q': "'{}' in parents".format(secondary_pictures_id)
                }).GetList()

                secondary_filenames = []

                file_list = filter(
                    lambda x: x['title'] != '.DS_Store',
                    file_list
                )

                file_list = sorted(
                    file_list,
                    key=lambda x: normalize_filename(x['title']))[1:]

                for drive_file in file_list:
                    local_filename = normalize_filename(drive_file['title'])

                    print('Downloading: {}'.format(local_filename))
                    drive_file.GetContentFile('solotodo_core/tmp/' +
                                              local_filename)

                    secondary_filenames.append(local_filename)
            else:
                secondary_filenames = None

            # Do the primary picture later to give it priority in case of name
            # clashes

            # Primary picture

            if primary_picture_id:
                remote_picture = drive.CreateFile(
                    {'id': primary_picture_id})
                primary_picture = normalize_filename(
                    remote_picture['title'])

                print('Downloading primary: {}'.format(primary_picture))
                remote_picture.GetContentFile('solotodo_core/tmp/' +
                                              primary_picture)
            else:
                primary_picture = None

            time.sleep(2)

            subprocess.run(['mogrify', '-trim', '-fuzz', '5%', '-resize',
                            '1500x1500', 'solotodo_core/tmp/*.jpg'])

            # subprocess.run(['mogrify', '-trim',
            #                 '-fuzz', '5%',
            #                 '-resize', '1300x1300',
            #                 '-background', 'white',
            #                 '-gravity', 'center',
            #                 '-extent', '1500x1500',
            #                 'solotodo_core/tmp/*.jpg'])

            # Upload primary picture

            if primary_picture:
                file_to_upload = open('solotodo_core/tmp/' +
                                      primary_picture, 'rb')
                uploaded_file_path = storage.save(
                    'products/' + primary_picture, file_to_upload)
                product.instance_model.picture = uploaded_file_path
                product.instance_model.save()
                print('Uploaded primary: {}'.format(uploaded_file_path))
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
