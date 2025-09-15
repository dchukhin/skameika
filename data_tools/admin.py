from django.contrib import admin

from . import models


@admin.register(models.CSVImport)
class CSVImportAdmin(admin.ModelAdmin):
    pass
