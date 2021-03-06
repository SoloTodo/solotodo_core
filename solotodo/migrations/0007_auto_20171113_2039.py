# -*- coding: utf-8 -*-
# Generated by Django 1.11.3 on 2017-11-13 20:39
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('solotodo', '0006_auto_20171110_1950'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='ApiClient',
            new_name='Website',
        ),
        migrations.AlterModelOptions(
            name='website',
            options={'ordering': ('name',), 'permissions': [('view_website', 'Can view the website'), ('view_website_leads', 'Can view the leads associated to this website')]},
        ),
        migrations.RenameField(
            model_name='lead',
            old_name='api_client',
            new_name='website',
        ),
    ]
