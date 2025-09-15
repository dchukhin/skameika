from django.contrib import admin

from . import models


@admin.register(models.CSVImport)
class CSVImportAdmin(admin.ModelAdmin):
    pass


@admin.register(models.TitleMapping)
class TitleMappingAdmin(admin.ModelAdmin):
    pass
