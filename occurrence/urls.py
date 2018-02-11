from django.conf.urls import url

from . import views


urlpatterns = [
    url(r'^transactions/$',
        views.transactions,
        name='transactions'),
    url(r'edit_transaction/(?P<type_cat>[-\w]+)/(?P<id>[0-9]+)/$',
        views.edit_transaction,
        name='edit_transaction'),
    url(r'^totals/$',
        views.totals,
        name='totals'),
    url(r'^running_totals/$',
        views.running_total_categories,
        name='running_totals')
]
