# Generated by Django 2.0.3 on 2019-02-20 13:06

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('solotodo', '0035_store_active_banner_update'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='store',
            options={'ordering': ['name'], 'permissions': (['view_store', 'Can view the store'], ['view_store_update_logs', 'Can view the store update logs'], ['view_store_stocks', 'Can view the store entities stock'], ['update_store_pricing', 'Can update the store pricing'], ['view_store_leads', 'View the leads associated to this store'], ['view_store_reports', 'Download the reports associated to this store'], ['backend_list_stores', 'Can view store list in backend'], ['view_store_banners', 'Can view store banners'])},
        ),
    ]
