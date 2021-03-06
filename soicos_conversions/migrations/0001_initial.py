# Generated by Django 2.0.3 on 2019-07-12 21:04

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('solotodo', '0056_auto_20190712_2019'),
    ]

    operations = [
        migrations.CreateModel(
            name='SoicosConversion',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('creation_date', models.DateTimeField()),
                ('validation_date', models.DateTimeField(blank=True, null=True)),
                ('ip', models.GenericIPAddressField()),
                ('transaction_id', models.CharField(max_length=256)),
                ('payout', models.DecimalField(decimal_places=2, max_digits=10)),
                ('transaction_total', models.DecimalField(decimal_places=2, max_digits=10)),
                ('status', models.IntegerField(choices=[(1, 'OK'), (2, 'Canceled'), (3, 'Pending'), (4, 'Blocked'), (5, 'Invalid country')])),
                ('lead', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='solotodo.Lead')),
            ],
        ),
    ]
