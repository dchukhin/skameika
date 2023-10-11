# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2017-09-24 21:18
from __future__ import unicode_literals

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('occurrence', '0005_auto_20170924_1637'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='month',
            options={'ordering': ('-year', '-month')},
        ),
        migrations.AlterField(
            model_name='transaction',
            name='month',
            field=models.ForeignKey(blank=True, help_text='The month that this Transaction occurred in.', on_delete=django.db.models.deletion.PROTECT, to='occurrence.Month'),
        ),
    ]
