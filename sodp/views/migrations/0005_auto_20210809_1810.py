# Generated by Django 3.1.12 on 2021-08-09 18:10

from django.conf import settings
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('views', '0004_auto_20210728_2110'),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name='view',
            name='views_user_index',
        ),
        migrations.AlterUniqueTogether(
            name='view',
            unique_together={('id', 'user')},
        ),
        migrations.AlterIndexTogether(
            name='view',
            index_together={('id', 'user')},
        ),
    ]
