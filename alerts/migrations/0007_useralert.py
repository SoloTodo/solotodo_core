# Generated by Django 2.0.3 on 2019-02-07 15:34

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('solotodo', '0032_auto_20190206_1357'),
        ('alerts', '0006_auto_20190207_1532'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserAlert',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('alert', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='alerts.Alert')),
                ('entity', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='solotodo.Entity')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ('alert',),
            },
        ),
    ]
