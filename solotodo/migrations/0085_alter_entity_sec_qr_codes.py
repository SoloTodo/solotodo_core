# Generated by Django 4.2.3 on 2023-10-12 18:50

import django.core.validators
from django.db import migrations, models
import re


class Migration(migrations.Migration):

    dependencies = [
        ('solotodo', '0084_entity_sec_qr_codes_product_sec_qr_codes'),
    ]

    operations = [
        migrations.AlterField(
            model_name='entity',
            name='sec_qr_codes',
            field=models.CharField(blank=True, db_index=True, max_length=255, null=True, validators=[django.core.validators.RegexValidator(re.compile('^\\d+(?:,\\d+)*\\Z'), code='invalid', message='Enter only digits separated by commas.')]),
        ),
    ]
