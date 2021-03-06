# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2017-10-14 18:04
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('occurrence', '0010_earningtransaction'),
    ]

    operations = [
        migrations.AddField(
            model_name='category',
            name='running_total_category',
            field=models.BooleanField(default=False, help_text='Whether this category should have a running total, rather than a regular total.'),
        ),
    ]
