# Generated by Django 2.2.13 on 2022-08-10 19:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('website_slides', '0002_websiteslide_label'),
    ]

    operations = [
        migrations.AlterField(
            model_name='websiteslide',
            name='categories',
            field=models.ManyToManyField(blank=True, null=True, to='solotodo.Category'),
        ),
    ]
