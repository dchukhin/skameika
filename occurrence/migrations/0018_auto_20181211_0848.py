# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-12-11 13:48
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('occurrence', '0017_auto_20180917_2046'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='earningtransaction',
            options={'ordering': ('-date', 'title', 'amount')},
        ),
        migrations.AlterModelOptions(
            name='expensetransaction',
            options={'ordering': ('-date', 'title', 'amount')},
        ),
    ]
