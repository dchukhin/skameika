from django.urls import path
from data_tools.views import upload_csv


urlpatterns = [
    path("upload-csv/", upload_csv, name="upload_csv"),
]
