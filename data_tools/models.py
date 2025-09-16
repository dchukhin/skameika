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


class TitleMapping(models.Model):
    """
    Model to map various transaction title variations to a canonical title.

    For example: 'Restaurant 1', 'Rest. 1', 'restaurant 1', 'RESTAURANT 1'
    would all map to 'Restaurant 1' as the canonical title.
    """

    source_title = models.CharField(
        max_length=255,
        unique=True,
        help_text="The title variation that appears in CSV files"
    )
    canonical_title = models.CharField(
        max_length=255,
        help_text="The canonical title to use for all matching variations"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['canonical_title', 'source_title']

    def __str__(self):
        return f"'{self.source_title}' -> '{self.canonical_title}'"
