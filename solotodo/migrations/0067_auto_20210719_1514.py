# Generated by Django 2.2.13 on 2021-07-19 15:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('solotodo', '0066_store_last_updated'),
    ]

    operations = [
        migrations.AlterField(
            model_name='rating',
            name='product_comments',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='rating',
            name='product_rating',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]