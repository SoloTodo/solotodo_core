# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('metamodel', '0006_auto_20150209_2016'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='instancemodel',
            options={'ordering': ('model', 'decimal_value', 'unicode_value', 'unicode_representation')},
        ),
    ]
