# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('metamodel', '0004_auto_20150206_1701'),
    ]

    operations = [
        migrations.AlterField(
            model_name='metafield',
            name='ordering',
            field=models.IntegerField(default=1),
            preserve_default=True,
        ),
    ]
