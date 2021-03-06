# Generated by Django 2.0.3 on 2019-07-05 20:45

from django.db import migrations, models
import django_redshift_backend.distkey


class Migration(migrations.Migration):

    dependencies = [
        ('lg_pricing', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='LgRsEntitySectionPosition',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('average_value', models.FloatField()),
                ('section_id', models.IntegerField()),
                ('section_name', models.CharField(max_length=256)),
                ('store_id', models.IntegerField()),
                ('store_name', models.CharField(max_length=256)),
                ('date', models.DateField()),
                ('entity_id', models.IntegerField()),
                ('entity_name', models.CharField(max_length=256)),
                ('category_id', models.IntegerField()),
                ('category_name', models.CharField(max_length=256)),
                ('product_id', models.IntegerField()),
                ('product_name', models.CharField(max_length=256)),
                ('brand_id', models.IntegerField()),
                ('brand_name', models.CharField(max_length=256)),
                ('sku', models.CharField(blank=True, max_length=256, null=True)),
                ('url', models.URLField(max_length=512)),
                ('latest_value', models.IntegerField())
            ],
            options={
                'ordering': ['date'],
                'indexes': [django_redshift_backend.distkey.DistKey(fields=['brand_id'], name='lg_pricing__brand_i_44794a_idx')]
            }
        )
    ]
