from django.http import HttpResponseNotAllowed
from django.shortcuts import render, redirect
from django.contrib import messages

from data_tools.forms import CSVUploadForm
from data_tools.models import CSVImport
from data_tools.utils import ingest_csv


def upload_csv(request):
    """Upload and ingest a CSV file."""
    if request.method == "POST":
        form = CSVUploadForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES["file"]
            csv_import_object = CSVImport.objects.create(file=csv_file)
            try:
                count_created, errors = ingest_csv(csv_import_object)

                if errors:
                    messages.error(
                        request, f"Error(s) processing file: {', '.join(errors)}"
                    )
                    render(request, "data_tools/upload_csv.html", {"form": form})
                else:
                    messages.success(
                        request,
                        f"CSV file uploaded. {count_created} transaction(s) created.",
                    )
                    return redirect("transactions")
            except Exception as e:
                messages.error(request, f"Error(s) processing file: {e}")
    elif request.method == "GET":
        form = CSVUploadForm()
    else:
        return HttpResponseNotAllowed([request.method])
    return render(request, "data_tools/upload_csv.html", {"form": form})
