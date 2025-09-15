from django.db import models

from django.db import models
from django.utils import timezone


class CSVImport(models.Model):
    """
    Model to track CSV imports.
    """

    file = models.FileField(upload_to="csv_imports/")
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"CSV Import on {self.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
