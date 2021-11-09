# Generated by Django 2.1.15 on 2021-06-18 12:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('flowspec', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='route',
            name='status',
            field=models.CharField(blank=True, choices=[('ACTIVE', 'ACTIVE'), ('ERROR', 'ERROR'), ('EXPIRED', 'EXPIRED'), ('PENDING', 'PENDING'), ('OUTOFSYNC', 'OUTOFSYNC'), ('INACTIVE', 'INACTIVE'), ('INACTIVE_TODELETE', 'INACTIVE_TODELETE'), ('ADMININACTIVE', 'ADMININACTIVE')], default='PENDING', max_length=20, null=True, verbose_name='Status'),
        ),
    ]