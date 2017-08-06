# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('metamodel', '0012_auto_20160115_1644'),
    ]

    operations = [
        migrations.AlterField(
            model_name='instancemodel',
            name='unicode_value',
            field=models.CharField(max_length=1024, null=True, blank=True),
        ),
    ]
