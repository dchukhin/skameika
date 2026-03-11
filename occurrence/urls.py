from django.urls import re_path

from . import views


urlpatterns = [
    re_path(r"^transactions/$", views.transactions, name="transactions"),
    re_path(
        r"^transactions/import/(?P<csv_import_id>[0-9]+)/$",
        views.csv_import_transactions,
        name="csv_import_transactions",
    ),
    re_path(
        r"edit_transaction/(?P<type_cat>[-\w]+)/(?P<id>[0-9]+)/$",
        views.edit_transaction,
        name="edit_transaction",
    ),
    re_path(r"copy_transactions/$", views.copy_transactions, name="copy_transactions"),
    re_path(r"^totals/$", views.totals, name="totals"),
    re_path(r"^running_totals/$", views.running_total_categories, name="running_totals"),
    re_path(
        r"^imports/$",
        views.csv_import_list,
        name="csv_import_list",
    ),
    re_path(r"^statistics-chart/$", views.statistics_chart_view, name="statistics_chart_view"),
    re_path(r"^budget/$", views.budget, name="budget"),
    re_path(
        r"^budget/edit/(?P<id>[0-9]+)/$",
        views.edit_budget_row,
        name="edit_budget_row",
    ),
    re_path(
        r"^budget/delete/(?P<id>[0-9]+)/$",
        views.delete_budget_row,
        name="delete_budget_row",
    ),
    re_path(r"^budget/copy/$", views.copy_budget, name="copy_budget"),
]
