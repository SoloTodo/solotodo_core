# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('metamodel', '0008_metafield_hidden'),
    ]

    operations = [
        migrations.AlterField(
            model_name='metafield',
            name='hidden',
            field=models.BooleanField(default=False),
            preserve_default=True,
        ),
    ]
