# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('metamodel', '0003_auto_20150205_2024'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='metafield',
            options={'ordering': ('parent', 'ordering')},
        ),
        migrations.AddField(
            model_name='metafield',
            name='ordering',
            field=models.IntegerField(default=1),
            preserve_default=False,
        ),
    ]
