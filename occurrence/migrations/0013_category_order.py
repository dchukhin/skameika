# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2017-10-22 18:24
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('occurrence', '0012_auto_20171014_1510'),
    ]

    operations = [
        migrations.AddField(
            model_name='category',
            name='order',
            field=models.PositiveSmallIntegerField(default=0),
        ),
    ]
