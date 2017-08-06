# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('metamodel', '0007_auto_20150213_1352'),
    ]

    operations = [
        migrations.AddField(
            model_name='metafield',
            name='hidden',
            field=models.BooleanField(default=True),
            preserve_default=True,
        ),
    ]
