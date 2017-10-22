from django.contrib import admin


from . import models


@admin.register(models.Category)
class CategoryAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name', )}
    list_display = ['name', 'type_cat', 'order']
    list_editable = ['order']
    list_filter = ['type_cat', 'total_type']


@admin.register(models.Month)
class MonthAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name', )}


@admin.register(models.ExpenseTransaction)
class ExpenseTransactionAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('title', )}


@admin.register(models.EarningTransaction)
class EarningTransactionAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('title', )}
