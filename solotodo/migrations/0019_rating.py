# Generated by Django 2.0.3 on 2018-03-19 11:27

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('solotodo', '0018_category_budget_ordering'),
    ]

    operations = [
        migrations.CreateModel(
            name='Rating',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('store_rating', models.IntegerField()),
                ('store_comments', models.TextField()),
                ('product_rating', models.IntegerField()),
                ('product_comments', models.TextField()),
                ('creation_date', models.DateTimeField(auto_now_add=True)),
                ('purchase_proof', models.FileField(upload_to='ratings')),
                ('approval_date', models.DateTimeField(blank=True, null=True)),
                ('ip', models.GenericIPAddressField()),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='solotodo.Product')),
                ('store', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='solotodo.Store')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-pk'],
            },
        ),
    ]
