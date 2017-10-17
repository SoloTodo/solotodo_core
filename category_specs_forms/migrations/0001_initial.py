# -*- coding: utf-8 -*-
# Generated by Django 1.11.3 on 2017-10-17 12:34
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='CategorySpecsFormFieldset',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('label', models.CharField(max_length=100)),
                ('ordering', models.IntegerField()),
            ],
            options={
                'ordering': ('layout', 'ordering'),
            },
        ),
        migrations.CreateModel(
            name='CategorySpecsFormFilter',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('label', models.CharField(max_length=100)),
                ('ordering', models.IntegerField()),
                ('continuous_range_step', models.IntegerField(blank=True, null=True)),
                ('continuous_range_unit', models.CharField(blank=True, max_length=20, null=True)),
            ],
            options={
                'ordering': ('fieldset', 'ordering'),
            },
        ),
        migrations.CreateModel(
            name='CategorySpecsFormLayout',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(blank=True, max_length=100, null=True)),
            ],
            options={
                'ordering': ('category', 'api_client', 'country', 'name'),
            },
        ),
        migrations.CreateModel(
            name='CategorySpecsFormOrder',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('label', models.CharField(max_length=100)),
                ('ordering', models.IntegerField()),
                ('suggested_use', models.CharField(choices=[('gte', 'High to low'), ('lte', 'Low to high'), ('both', 'Both')], max_length=20)),
                ('layout', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='orders', to='category_specs_forms.CategorySpecsFormLayout')),
            ],
            options={
                'ordering': ('layout', 'ordering'),
            },
        ),
    ]