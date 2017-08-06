# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('metamodel', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='metamodel',
            name='name',
            field=models.CharField(unique=True, max_length=100),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='instancefield',
            unique_together=set([('parent', 'value')]),
        ),
        migrations.AlterUniqueTogether(
            name='metafield',
            unique_together=set([('parent', 'name')]),
        ),
    ]
