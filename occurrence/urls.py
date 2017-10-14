from django.conf.urls import url

from . import views


urlpatterns = [
    url(r'^transactions/$',
        views.transactions,
        name='transactions'),
    url(r'^totals/$',
        views.totals,
        name='totals'),
    url(r'^running_totals/$',
        views.running_total_categories,
        name='running_totals')
]
