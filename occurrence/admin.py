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
    list_filter = ('category', 'month', )
    search_fields = ('title', 'category__name', )
    list_display = ('title', 'amount', 'date', 'month', )


@admin.register(models.EarningTransaction)
class EarningTransactionAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('title', )}
    list_filter = ('category', 'month', )
    search_fields = ('title', 'category__name', )
    list_display = ('title', 'amount', 'date', 'month', )


@admin.register(models.Statistic)
class StatisticAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name', )}
    list_display = ['name', 'order']
    list_editable = ['order']


@admin.register(models.MonthlyStatistic)
class MonthlyStatisticAdmin(admin.ModelAdmin):
    list_display = ['statistic', 'month', 'amount']
    list_filter = ['statistic', 'month']
