# Generated by Django 2.0.3 on 2019-06-28 16:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('solotodo', '0051_auto_20190628_1434'),
    ]

    operations = [
        migrations.AlterField(
            model_name='entityhistory',
            name='timestamp',
            field=models.DateTimeField(db_index=True),
        ),
    ]
