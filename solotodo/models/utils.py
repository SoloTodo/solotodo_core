SOLOTODO_COM_SITE = None


def solotodo_com_site():
    from django.contrib.sites.models import Site
    from django.conf import settings

    global SOLOTODO_COM_SITE

    if not SOLOTODO_COM_SITE:
        SOLOTODO_COM_SITE = Site.objects.get(pk=settings.SOLOTODO_COM_SITE_ID)

    return SOLOTODO_COM_SITE


def rs_refresh_model(model, table_name, fields):
    import csv
    import io
    from django.conf import settings
    from django.core.files.base import ContentFile
    from django.db import connections
    from solotodo_core.s3utils import PrivateS3Boto3Storage

    # Generate and upload file

    output = io.StringIO()
    writer = csv.writer(output)

    for instance in model.objects.all():
        row = [getattr(instance, field) for field in fields]
        writer.writerow(row)

    output.seek(0)
    file_value = output.getvalue().encode('utf-8')
    output.close()

    file_for_upload = ContentFile(file_value)

    storage = PrivateS3Boto3Storage()
    storage.file_overwrite = True

    filepath = 'analytics/{}.csv'.format(table_name)
    storage.save(filepath, file_for_upload)

    # Load file in Redshift

    cursor = connections['analytics'].cursor()
    cursor.execute('TRUNCATE {}'.format(table_name))
    command = """
copy {} from 's3://{}/analytics/{}.csv'
credentials 'aws_access_key_id={};aws_secret_access_key={}'
csv;
""".format(
        table_name,
        settings.AWS_STORAGE_BUCKET_NAME,
        table_name,
        settings.AWS_ACCESS_KEY_ID,
        settings.AWS_SECRET_ACCESS_KEY
    )
    cursor.execute(command)
    cursor.close()


def rs_refresh_entries(base_qs, table_name, last_modified_field, fields):
    import csv
    import io
    import time
    from django.conf import settings
    from django.core.files.base import ContentFile
    from django.db import connections
    from solotodo_core.s3utils import PrivateS3Boto3Storage

    transaction_id = int(time.time())

    # Find last modification date
    cursor = connections['analytics'].cursor()

    cursor.execute("""
SELECT {} FROM {} ORDER BY {} DESC LIMIT 1
""".format(last_modified_field, table_name, last_modified_field))
    row = cursor.fetchone()

    qs = base_qs

    if row:
        filter_params = {'{}__gte'.format(last_modified_field): row[0]}
        qs = qs.filter(**filter_params)

    page_size = 100000
    page = 0

    while True:
        print(page)
        output = io.StringIO()
        writer = csv.writer(output)

        segment = qs[page*page_size:(page+1)*page_size]

        if not segment:
            break

        ids_for_deletion = []

        print('creating data')
        for instance in segment.iterator():
            ids_for_deletion.append(str(instance.id))
            row = [getattr(instance, field, '\x00') for field in fields]
            writer.writerow(row)

        output.seek(0)
        file_value = output.getvalue().encode('utf-8')
        output.close()
        file_for_upload = ContentFile(file_value)

        storage = PrivateS3Boto3Storage()
        storage.file_overwrite = True

        filepath = 'analytics/{}-{}.{}.csv'.format(
            transaction_id, table_name, page)
        print('uploading data')
        storage.save(filepath, file_for_upload)

        # Delete old IDs

        print('deleting ids')
        cursor.execute("""
DELETE FROM {} WHERE id IN ({})
""".format(table_name, ','.join(ids_for_deletion)))

        page += 1

    # Load files in Redshift

    print('copy')
    command = """
copy {} from 's3://{}/analytics/{}-{}'
credentials 'aws_access_key_id={};aws_secret_access_key={}'
csv;
""".format(
        table_name,
        settings.AWS_STORAGE_BUCKET_NAME,
        transaction_id,
        table_name,
        settings.AWS_ACCESS_KEY_ID,
        settings.AWS_SECRET_ACCESS_KEY
    )
    cursor.execute(command)

    cursor.close()
