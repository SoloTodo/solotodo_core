# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('metamodel', '0002_auto_20150203_1533'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='instancemodel',
            options={'ordering': ('model',)},
        ),
        migrations.AlterModelOptions(
            name='metafield',
            options={'ordering': ('parent', 'name')},
        ),
        migrations.AlterModelOptions(
            name='metamodel',
            options={'ordering': ('name',)},
        ),
        migrations.AlterField(
            model_name='instancemodel',
            name='decimal_value',
            field=models.DecimalField(null=True, max_digits=20, decimal_places=5, blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='instancemodel',
            name='unicode_representation',
            field=models.CharField(max_length=255, null=True, blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='instancemodel',
            name='unicode_value',
            field=models.CharField(max_length=255, null=True, blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='metamodel',
            name='type',
            field=models.CharField(max_length=100, choices=[(b'BooleanField', b'BooleanField'), (b'CharField', b'CharField'), (b'DateField', b'DateField'), (b'DateTimeField', b'DateTimeField'), (b'DecimalField', b'DecimalField'), (b'FileField', b'FileField'), (b'IntegerField', b'IntegerField'), (b'MetaModel', b'MetaModel')]),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='instancefield',
            unique_together=set([]),
        ),
    ]
