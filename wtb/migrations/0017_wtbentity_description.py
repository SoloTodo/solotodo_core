# Generated by Django 2.2.13 on 2022-01-17 17:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('wtb', '0016_auto_20200817_2104'),
    ]

    operations = [
        migrations.AddField(
            model_name='wtbentity',
            name='description',
            field=models.TextField(blank=True, null=True),
        ),
    ]
