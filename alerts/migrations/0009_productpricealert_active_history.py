# Generated by Django 2.0.3 on 2019-08-08 21:02

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('alerts', '0008_productpricealert_productpricealerthistory_productpricealerthistoryentry'),
    ]

    operations = [
        migrations.AddField(
            model_name='productpricealert',
            name='active_history',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='alerts.ProductPriceAlertHistory'),
        ),
    ]