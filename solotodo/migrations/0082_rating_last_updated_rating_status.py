# Generated by Django 4.2.3 on 2023-08-22 19:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('solotodo', '0081_alter_entity_ean_alter_entitylog_ean_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='rating',
            name='last_updated',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name='rating',
            name='status',
            field=models.IntegerField(choices=[(1, 'Pending'), (2, 'Approved'), (3, 'Rejected'), (4, 'Investigating')], default=1),
        ),
    ]