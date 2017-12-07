# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='InstanceField',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='InstanceModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('decimal_value', models.DecimalField(null=True, max_digits=15, decimal_places=5)),
                ('unicode_value', models.CharField(max_length=255, null=True)),
                ('unicode_representation', models.CharField(max_length=255, null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='MetaField',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100)),
                ('nullable', models.BooleanField(default=False)),
                ('multiple', models.BooleanField(default=False)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='MetaModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100)),
                ('type', models.CharField(max_length=100, choices=[(b'BooleanField', b'BooleanField'), (b'CharField', b'CharField'), (b'DateField', b'DateField'), (b'DateTimeField', b'DateTimeField'), (b'DecimalField', b'DecimalField'), (b'FileField', b'FileField'), (b'IntegerField', b'IntegerField'), (b'NullBooleanField', b'NullBooleanField'), (b'TextField', b'TextField'), (b'MetaModel', b'MetaModel')])),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='metafield',
            name='model',
            field=models.ForeignKey(related_name='fields_usage', to='metamodel.MetaModel', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='metafield',
            name='parent',
            field=models.ForeignKey(related_name='fields', to='metamodel.MetaModel', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='instancemodel',
            name='model',
            field=models.ForeignKey(to='metamodel.MetaModel', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='instancefield',
            name='field',
            field=models.ForeignKey(to='metamodel.MetaField', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='instancefield',
            name='parent',
            field=models.ForeignKey(related_name='fields', to='metamodel.InstanceModel', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='instancefield',
            name='value',
            field=models.ForeignKey(related_name='fields_usage', to='metamodel.InstanceModel', on_delete=models.CASCADE),
            preserve_default=True,
        ),
    ]
