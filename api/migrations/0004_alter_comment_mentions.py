# Generated by Django 5.1.6 on 2025-04-28 11:09

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0003_task_due_date'),
    ]

    operations = [
        migrations.AlterField(
            model_name='comment',
            name='mentions',
            field=models.ManyToManyField(blank=True, null=True, related_name='mentions', to=settings.AUTH_USER_MODEL),
        ),
    ]
