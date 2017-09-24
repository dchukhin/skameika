from django.conf.urls import url

from . import views


urlpatterns = [
    url(r'^transactions/$',
        views.transactions,
        name='transactions'),
    url(r'^totals/$',
        views.totals,
        name='totals'),
]
