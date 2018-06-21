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
    cursor.execute
    cursor.close()

