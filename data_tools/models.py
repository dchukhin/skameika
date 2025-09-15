from django.db import models

from django.db import models
from django.utils import timezone


class CSVImport(models.Model):
    """
    Model to track CSV imports.
    """

    file = models.FileField(upload_to="csv_imports/")
    created_at = models.DateTimeField(default=timezone.now)
    rows_created = models.PositiveIntegerField(default=0, help_text="Number of transactions created from this import")
    rows_skipped = models.PositiveIntegerField(default=0, help_text="Number of rows skipped during this import")

    def __str__(self):
        return f"CSV Import on {self.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
