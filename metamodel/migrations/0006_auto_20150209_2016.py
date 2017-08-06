# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('metamodel', '0005_auto_20150206_1703'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='instancemodel',
            options={'ordering': ('model', 'unicode_representation', 'unicode_value', 'decimal_value')},
        ),
        migrations.RemoveField(
            model_name='metamodel',
            name='type',
        ),
    ]
