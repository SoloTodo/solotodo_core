# -*- coding: utf-8 -*-
# Generated by Django 1.11.3 on 2017-07-12 19:38
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0008_alter_user_username_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='SoloTodoUser',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('email', models.EmailField(db_index=True, max_length=255, unique=True, verbose_name='email address')),
                ('is_staff', models.BooleanField(default=False, help_text='Designates whether the user can log into this admin site.', verbose_name='staff status')),
                ('is_active', models.BooleanField(default=True, help_text='Designates whether this user should be treated as active. Unselect this instead of deleting accounts.', verbose_name='active')),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='date joined')),
                ('first_name', models.CharField(blank=True, max_length=30, null=True, verbose_name='first name')),
                ('last_name', models.CharField(blank=True, max_length=30, null=True, verbose_name='last name')),
                ('groups', models.ManyToManyField(blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', related_name='user_set', related_query_name='user', to='auth.Group', verbose_name='groups')),
                ('user_permissions', models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='user_set', related_query_name='user', to='auth.Permission', verbose_name='user permissions')),
            ],
            options={
                'verbose_name': 'SoloTodo User',
                'verbose_name_plural': 'SoloTodo Users',
            },
        ),
        migrations.CreateModel(
            name='Country',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
            ],
        ),
        migrations.CreateModel(
            name='Currency',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('iso_code', models.CharField(max_length=10)),
                ('decimal_places', models.IntegerField()),
                ('prefix', models.CharField(default='$', max_length=10)),
                ('exchange_rate', models.DecimalField(decimal_places=2, max_digits=8)),
                ('exchange_rate_last_updated', models.DateTimeField()),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='Entity',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(db_index=True, max_length=256)),
                ('cell_plan_name', models.CharField(blank=True, db_index=True, max_length=50, null=True)),
                ('part_number', models.CharField(blank=True, db_index=True, max_length=50, null=True)),
                ('sku', models.CharField(blank=True, db_index=True, max_length=50, null=True)),
                ('key', models.CharField(db_index=True, max_length=256)),
                ('url', models.URLField(db_index=True, max_length=512, unique=True)),
                ('discovery_url', models.URLField(db_index=True, max_length=512, unique=True)),
                ('description', models.TextField(db_index=True)),
                ('is_visible', models.BooleanField(default=True)),
                ('latest_association_date', models.DateTimeField(blank=True, null=True)),
                ('creation_date', models.DateTimeField(auto_now_add=True)),
                ('last_updated', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='EntityHistory',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(db_index=True)),
                ('stock', models.IntegerField(db_index=True)),
                ('normal_price', models.DecimalField(decimal_places=2, max_digits=12)),
                ('offer_price', models.DecimalField(decimal_places=2, max_digits=12)),
                ('cell_monthly_payment', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ('entity', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='solotodo.Entity')),
            ],
            options={
                'ordering': ['entity', 'date'],
            },
        ),
        migrations.CreateModel(
            name='Product',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(db_index=True, max_length=255)),
                ('part_number', models.CharField(db_index=True, max_length=255)),
                ('creation_date', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('last_updated', models.DateTimeField(auto_now=True)),
                ('creator', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='ProductType',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(db_index=True, max_length=255, unique=True)),
                ('storescraper_name', models.CharField(db_index=True, max_length=255)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='Store',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(db_index=True, max_length=255, unique=True)),
                ('is_active', models.BooleanField(default=True)),
                ('storescraper_class', models.CharField(db_index=True, max_length=255)),
                ('storescraper_extra_args', models.CharField(blank=True, max_length=255, null=True)),
                ('country', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='solotodo.Country')),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.AddField(
            model_name='product',
            name='product_type',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='solotodo.ProductType'),
        ),
        migrations.AddField(
            model_name='entity',
            name='active_registry',
            field=models.OneToOneField(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to='solotodo.EntityHistory'),
        ),
        migrations.AddField(
            model_name='entity',
            name='cell_plan',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to='solotodo.Product'),
        ),
        migrations.AddField(
            model_name='entity',
            name='currency',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='solotodo.Currency'),
        ),
        migrations.AddField(
            model_name='entity',
            name='product',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='solotodo.Product'),
        ),
        migrations.AddField(
            model_name='entity',
            name='product_type',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='solotodo.ProductType'),
        ),
        migrations.AddField(
            model_name='entity',
            name='scraped_product_type',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='solotodo.ProductType'),
        ),
        migrations.AddField(
            model_name='entity',
            name='store',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='solotodo.Store'),
        ),
        migrations.AddField(
            model_name='country',
            name='currency',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='solotodo.Currency'),
        ),
        migrations.AlterUniqueTogether(
            name='entityhistory',
            unique_together=set([('entity', 'date')]),
        ),
        migrations.AlterUniqueTogether(
            name='entity',
            unique_together=set([('store', 'key')]),
        ),
    ]
