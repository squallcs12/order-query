# Generated by Django 5.0.6 on 2024-07-05 02:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('order', '0002_order_status_alter_orderstatus_status'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='order',
            index=models.Index(models.F('status'), name='index_by_status'),
        ),
    ]