# Generated by Django 2.2.27 on 2022-03-10 15:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('flowspec', '0002_auto_20210618_1202'),
    ]

    operations = [
        migrations.AlterField(
            model_name='route',
            name='destination',
            field=models.CharField(help_text='Network address. Use address/CIDR notation', max_length=49, verbose_name='Destination Address'),
        ),
        migrations.AlterField(
            model_name='route',
            name='source',
            field=models.CharField(help_text='Network address. Use address/CIDR notation', max_length=49, verbose_name='Source Address'),
        ),
        migrations.AlterField(
            model_name='route',
            name='status',
            field=models.CharField(blank=True, choices=[('ACTIVE', 'ACTIVE'), ('ERROR', 'ERROR'), ('EXPIRED', 'EXPIRED'), ('PENDING', 'PENDING'), ('PENDING_TODELETE', 'PENDING_TODELETE'), ('OUTOFSYNC', 'OUTOFSYNC'), ('INACTIVE', 'INACTIVE'), ('INACTIVE_TODELETE', 'INACTIVE_TODELETE'), ('ADMININACTIVE', 'ADMININACTIVE')], default='PENDING', max_length=20, null=True, verbose_name='Status'),
        ),
    ]
