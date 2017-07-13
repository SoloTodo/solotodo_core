# -*- coding: utf-8 -*-
# Generated by Django 1.11.3 on 2017-07-13 20:29
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('solotodo', '0003_auto_20170712_1709'),
    ]

    operations = [
        migrations.RenameField(
            model_name='entity',
            old_name='active_registry',
            new_name='latest_registry',
        ),
        migrations.AlterField(
            model_name='entityhistory',
            name='normal_price',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True),
        ),
        migrations.AlterField(
            model_name='entityhistory',
            name='offer_price',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True),
        ),
    ]
