# -*- coding: utf-8 -*-
# Generated by Django 1.11.3 on 2017-07-14 21:59
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
import storages.backends.s3boto3


class Migration(migrations.Migration):

    dependencies = [
        ('solotodo', '0006_auto_20170714_1159'),
    ]

    operations = [
        migrations.CreateModel(
            name='StoreUpdateLog',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.IntegerField(choices=[(1, 'Pending'), (2, 'In process'), (3, 'Sucess'), (4, 'Error')], default=1)),
                ('creation_date', models.DateTimeField(auto_now_add=True)),
                ('last_updated', models.DateTimeField(auto_now=True)),
                ('discovery_url_concurrency', models.IntegerField()),
                ('products_for_url_concurrency', models.IntegerField()),
                ('registry_file', models.FileField(storage=storages.backends.s3boto3.S3Boto3Storage(default_acl='private'), upload_to='')),
                ('product_types', models.ManyToManyField(to='solotodo.ProductType')),
                ('store', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='solotodo.Store')),
            ],
            options={
                'ordering': ['store', '-creation_date'],
            },
        ),
    ]
