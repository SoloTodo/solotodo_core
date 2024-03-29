# Generated by Django 2.2.13 on 2023-04-04 19:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('solotodo', '0076_auto_20221111_1940'),
    ]

    operations = [
        migrations.AddField(
            model_name='store',
            name='preferred_payment_method',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='entity',
            name='condition',
            field=models.URLField(choices=[('https://schema.org/DamagedCondition', 'Damaged'), ('https://schema.org/NewCondition', 'New'), ('https://schema.org/RefurbishedCondition', 'Refurbished'), ('https://schema.org/UsedCondition', 'Used'), ('https://schema.org/OpenBoxCondition', 'Open Box')]),
        ),
        migrations.AlterField(
            model_name='entity',
            name='scraped_condition',
            field=models.URLField(choices=[('https://schema.org/DamagedCondition', 'Damaged'), ('https://schema.org/NewCondition', 'New'), ('https://schema.org/RefurbishedCondition', 'Refurbished'), ('https://schema.org/UsedCondition', 'Used'), ('https://schema.org/OpenBoxCondition', 'Open Box')]),
        ),
    ]
