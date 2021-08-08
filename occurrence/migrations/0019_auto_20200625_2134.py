# Generated by Django 2.2 on 2020-06-26 01:34

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('occurrence', '0018_auto_20181211_0848'),
    ]

    operations = [
        migrations.AlterField(
            model_name='earningtransaction',
            name='category',
            field=models.ForeignKey(limit_choices_to={'type_cat': 'income'}, on_delete=django.db.models.deletion.CASCADE, to='occurrence.Category'),
        ),
        migrations.AlterField(
            model_name='expensetransaction',
            name='category',
            field=models.ForeignKey(limit_choices_to={'type_cat': 'expense'}, on_delete=django.db.models.deletion.CASCADE, to='occurrence.Category'),
        ),
    ]