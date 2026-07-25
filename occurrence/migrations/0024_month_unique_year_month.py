from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("occurrence", "0023_replace_unique_together_with_constraints"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="month",
            constraint=models.UniqueConstraint(
                fields=("year", "month"), name="unique_month_year_month"
            ),
        ),
    ]
