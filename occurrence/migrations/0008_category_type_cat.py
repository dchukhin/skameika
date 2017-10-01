# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2017-10-01 00:06
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('occurrence', '0007_month_slug'),
    ]

    operations = [
        migrations.AddField(
            model_name='category',
            name='type_cat',
            field=models.CharField(choices=[('income', 'Income'), ('expense', 'Expense')], default='expense', max_length=20),
        ),
    ]