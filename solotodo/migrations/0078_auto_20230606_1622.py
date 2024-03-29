# Generated by Django 2.2.13 on 2023-06-06 16:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('solotodo', '0077_auto_20230404_1938'),
    ]

    operations = [
        migrations.AlterField(
            model_name='entity',
            name='condition',
            field=models.URLField(choices=[('https://schema.org/DamagedCondition', 'Damaged'), ('https://schema.org/NewCondition', 'New'), ('https://schema.org/RefurbishedCondition', 'Refurbished'), ('https://schema.org/UsedCondition', 'Used'), ('https://schema.org/OpenBoxCondition', 'Open Box')], db_index=True),
        ),
        migrations.AlterField(
            model_name='entity',
            name='scraped_condition',
            field=models.URLField(choices=[('https://schema.org/DamagedCondition', 'Damaged'), ('https://schema.org/NewCondition', 'New'), ('https://schema.org/RefurbishedCondition', 'Refurbished'), ('https://schema.org/UsedCondition', 'Used'), ('https://schema.org/OpenBoxCondition', 'Open Box')], db_index=True),
        ),
    ]
