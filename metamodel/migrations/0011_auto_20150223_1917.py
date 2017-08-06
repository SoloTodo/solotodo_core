# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('metamodel', '0010_auto_20150223_1531'),
    ]

    operations = [
        migrations.AlterField(
            model_name='metamodel',
            name='ordering_field',
            field=models.CharField(max_length=50, null=True, blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='metamodel',
            name='unicode_template',
            field=models.CharField(max_length=255, null=True, blank=True),
            preserve_default=True,
        ),
    ]
