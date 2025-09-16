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
]
