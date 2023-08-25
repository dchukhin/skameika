from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.utils.translation import gettext_lazy as _

from . import models


class MonthFilter(SimpleListFilter):
    title = _('month')

    parameter_name = 'month'

    def lookups(self, request, model_admin):
        """Return the Month choices, in reverse chronological order."""
        qs = model_admin.get_queryset(request)
        return [
            (i['month_id'], i['month__name'])
            for i in qs.values('month__name', 'month_id').distinct().order_by('month')
        ]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(month__exact=self.value())


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
    list_display = ('id', 'date', 'amount', 'title', 'description')


@admin.register(models.EarningTransaction)
class EarningTransactionAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('title', )}
    list_filter = ('category', 'month', )
    search_fields = ('title', 'category__name', )
    list_display = ('id', 'title', 'amount', 'date', 'month', 'description')


@admin.register(models.Statistic)
class StatisticAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name', )}
    list_display = ['name', 'order']
    list_editable = ['order']


@admin.register(models.MonthlyStatistic)
class MonthlyStatisticAdmin(admin.ModelAdmin):
    list_display = ['statistic', 'month', 'amount']
    list_filter = ['statistic', MonthFilter]


@admin.register(models.ExpectedMonthlyCategoryTotal)
class ExpectedMonthlyCategoryTotalAdmin(admin.ModelAdmin):
    list_display = ['category', 'month', 'amount']
    list_filter = ['month', 'category']
