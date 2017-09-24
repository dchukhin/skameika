from django.contrib import admin


from . import models


@admin.register(models.Category)
class CategoryAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name', )}


@admin.register(models.Month)
class MonthAdmin(admin.ModelAdmin):
    pass


@admin.register(models.Transaction)
class TransactionAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('title', )}
