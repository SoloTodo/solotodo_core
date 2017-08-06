# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('metamodel', '0011_auto_20150223_1917'),
    ]

    operations = [
        migrations.AlterField(
            model_name='instancemodel',
            name='decimal_value',
            field=models.DecimalField(null=True, max_digits=200, decimal_places=5, blank=True),
        ),
    ]
