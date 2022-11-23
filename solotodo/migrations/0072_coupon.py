# Generated by Django 2.2.13 on 2022-10-06 16:06

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('solotodo', '0071_auto_20220905_1940'),
    ]

    operations = [
        migrations.CreateModel(
            name='Coupon',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('amount_type', models.IntegerField(choices=[(1, 'Raw amount'), (2, 'Percentage')])),
                ('store', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='solotodo.Store')),
            ],
            options={
                'ordering': ('-pk',),
            },
        ),
    ]