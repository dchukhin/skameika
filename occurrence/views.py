from datetime import date

from django.contrib import messages
from django.db.models import DecimalField, F, Q, Sum, Value
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.dateparse import parse_date
from django.utils.text import slugify
from django.views.decorators.http import require_http_methods

from data_tools.models import CSVImport
from . import forms, models, utils


def transactions(request, *args, **kwargs):
    """Show all current transactions."""
    # Get the current_month, either from the request kwargs, or use the today's month
    if request.GET.get("month"):
        current_month = get_object_or_404(
            models.Month.objects.all(), slug=request.GET.get("month")
        )
    else:
        current_month = models.Month.objects.get_or_create(
            year=date.today().year,
            month=date.today().month,
            name=date.today().strftime("%B, %Y"),
        )[0]
    expense_transactions = models.ExpenseTransaction.objects.filter(
        month=current_month
    ).select_related("category")
    earning_transactions = models.EarningTransaction.objects.filter(
        month=current_month
    ).select_related("category")
    expense_transaction_titles = (
        models.ExpenseTransaction.objects.order_by("title")
        .values_list("title", flat=True)
        .distinct("title")
    )
    earning_transaction_titles = (
        models.EarningTransaction.objects.order_by("title")
        .values_list("title", flat=True)
        .distinct("title")
    )

    context = {
        "expense_transactions": expense_transactions,
        "earning_transactions": earning_transactions,
        "expense_form": forms.ExpenseTransactionForm(),
        "earning_form": forms.EarningTransactionForm(),
        "current_month": current_month,
        "months": models.Month.objects.all(),
        "expense_transaction_choices": expense_transaction_titles,
        "earning_transaction_choices": earning_transaction_titles,
        "expense_transaction_constant": models.Category.TYPE_EXPENSE,
        "earning_transaction_constant": models.Category.TYPE_EARNING,
        "show_new_expense_transaction_form": True,
        "show_new_earning_transaction_form": True,
    }
    if request.method == "POST":
        # Is this for an expense, or an earning?
        if request.POST.get("form_type") == "expense":
            # Use the ExpenseTransactionForm for expense POSTs
            form = forms.ExpenseTransactionForm(request.POST)
        elif request.POST.get("form_type") == "earning":
            # Use the EarningTransactionForm for earning POSTs
            form = forms.EarningTransactionForm(request.POST)

        # If the form is valid, then save the form
        if form.is_valid():
            form.save()
        else:
            # The form is not valid, so return the invalid form to the template
            context["expense_form"] = form
    return render(request, "occurrence/transactions.html", context)


@require_http_methods(["GET"])
def totals(request, *args, **kwargs):
    """Show totals (for transactions) by category."""
    month_slug = request.GET.get("month")
    # If the user did not provide a month_slug, then redirect to the totals
    # for the current month
    if not month_slug:
        current_month = models.Month.objects.get_or_create(
            year=date.today().year,
            month=date.today().month,
            name=date.today().strftime("%B, %Y"),
            slug=slugify(date.today().strftime("%B, %Y")),
        )[0]
        return redirect("{}?month={}".format(reverse("totals"), current_month.slug))

    month = get_object_or_404(models.Month.objects.all(), slug=month_slug)

    # Get budget data for this month (used by get_transactions_regular_totals)
    budget_by_category = {
        row.category_id: row.amount
        for row in models.ExpectedMonthlyCategoryTotal.objects.filter(month=month)
    }

    # Get the expense totals for this month, enriched with budget data
    expense_categories, expense_total = utils.get_transactions_regular_totals(
        month,
        type_cat=models.Category.TYPE_EXPENSE,
        budget_by_category=budget_by_category,
    )
    # Get the earning totals for this month, enriched with budget data
    earning_categories, earning_total = utils.get_transactions_regular_totals(
        month,
        type_cat=models.Category.TYPE_EARNING,
        budget_by_category=budget_by_category,
    )

    # Get the MonthlyStatistic for this Month
    monthly_statistics = models.MonthlyStatistic.objects.filter(month=month)

    expense_budget_total = sum(
        cat["budgeted"] for cat in expense_categories.values() if cat.get("budgeted") is not None
    ) or None
    earning_budget_total = sum(
        cat["budgeted"] for cat in earning_categories.values() if cat.get("budgeted") is not None
    ) or None

    context = {
        "expense_categories": expense_categories,
        "expense_total": expense_total,
        "expense_budget_total": expense_budget_total,
        "earning_categories": earning_categories,
        "earning_total": earning_total,
        "earning_budget_total": earning_budget_total,
        "total": earning_total - expense_total,
        "budget_total": (earning_budget_total - expense_budget_total)
        if earning_budget_total is not None and expense_budget_total is not None
        else None,
        "monthly_statistics": monthly_statistics,
        "months": models.Month.objects.all(),
        "active_month": month,
        "expense_chart_data": [
            {"name": cat["name"], "total": float(cat["total"])}
            for cat in expense_categories.values()
        ],
        "earning_chart_data": [
            {"name": cat["name"], "total": float(cat["total"])}
            for cat in earning_categories.values()
        ],
    }
    return render(request, "occurrence/totals.html", context)


@require_http_methods(["GET"])
def running_total_categories(request):
    """The view for Categories that have a running total, rather than the regular total."""
    categories = models.Category.objects.filter(
        total_type=models.Category.TOTAL_TYPE_RUNNING
    ).annotate(
        total=Sum(
            F("expensetransaction__amount") * Value("-1"), output_field=DecimalField()
        ),
    )
    # For each Category, attach a queryset of ExpenseTransactions that have a
    # running_total_amount fiels
    for category in categories:
        category.expense_transactions = utils.get_expensetransactions_running_totals(
            category
        )

    context = {"categories": categories}
    return render(request, "occurrence/running_totals.html", context)


@require_http_methods(["GET", "POST"])
def edit_transaction(request, type_cat, id):
    """Edit a transaction."""
    # Attempt to find the transaction, based on the type_cat
    if type_cat == models.Category.TYPE_EXPENSE:
        transaction = get_object_or_404(models.ExpenseTransaction.objects.all(), pk=id)
    elif type_cat == models.Category.TYPE_EARNING:
        transaction = get_object_or_404(models.EarningTransaction.objects.all(), pk=id)
    else:
        raise Http404("Category type not recognized")

    if request.method == "POST":
        if type_cat == models.Category.TYPE_EXPENSE:
            form = forms.ExpenseTransactionForm(request.POST, instance=transaction)
        elif type_cat == models.Category.TYPE_EARNING:
            form = forms.EarningTransactionForm(request.POST, instance=transaction)
        # If the form is valid, save the object
        if form.is_valid():
            form.save()
            # If there is a next_url parameter, then redirect the user to it.
            next_url = request.GET.get("next")
            if next_url and next_url.startswith("/"):
                return redirect(next_url)
            # Redirect the user to the transactions view for the month that this
            # transaction is in
            return redirect(
                "{}?month={}".format(reverse("transactions"), transaction.month.slug)
            )
    else:
        if type_cat == models.Category.TYPE_EXPENSE:
            form = forms.ExpenseTransactionForm(instance=transaction)
        elif type_cat == models.Category.TYPE_EARNING:
            form = forms.EarningTransactionForm(instance=transaction)
    context = {"form": form, "transaction": transaction, "type_cat": type_cat}
    return render(request, "occurrence/edit_transaction.html", context)


@require_http_methods(["GET"])
def csv_import_list(request):
    """Show a list of all CSVImport objects."""
    csv_imports = CSVImport.objects.all().order_by("-created_at")

    context = {
        "csv_imports": csv_imports,
    }
    return render(request, "occurrence/csv_import_list.html", context)


@require_http_methods(["GET"])
def csv_import_transactions(request, csv_import_id):
    """Show all transactions for a specific CSVImport."""
    if not csv_import_id:
        raise Http404("CSV Import ID is required")

    # Get the CSVImport object
    csv_import = get_object_or_404(CSVImport, pk=csv_import_id)

    # Get transactions filtered by CSV import
    expense_transactions = models.ExpenseTransaction.objects.filter(
        csv_import=csv_import
    ).select_related("category")
    earning_transactions = models.EarningTransaction.objects.filter(
        csv_import=csv_import
    ).select_related("category")

    context = {
        "expense_transactions": expense_transactions,
        "earning_transactions": earning_transactions,
        "csv_import": csv_import,
        "expense_transaction_constant": models.Category.TYPE_EXPENSE,
        "earning_transaction_constant": models.Category.TYPE_EARNING,
    }
    return render(request, "occurrence/transactions.html", context)


def budget(request):
    """Show and manage budget rows for a month."""
    if request.GET.get("month"):
        current_month = get_object_or_404(
            models.Month.objects.all(), slug=request.GET.get("month")
        )
    else:
        current_month = models.Month.objects.get_or_create(
            year=date.today().year,
            month=date.today().month,
            name=date.today().strftime("%B, %Y"),
        )[0]

    expense_form = forms.ExpenseBudgetRowForm()
    earning_form = forms.EarningBudgetRowForm()

    if request.method == "POST":
        form_type = request.POST.get("form_type")
        if form_type == models.Category.TYPE_EXPENSE:
            form = forms.ExpenseBudgetRowForm(request.POST)
        elif form_type == models.Category.TYPE_EARNING:
            form = forms.EarningBudgetRowForm(request.POST)
        else:
            form = None

        if form and form.is_valid():
            budget_row = form.save(commit=False)
            budget_row.month = current_month
            # Check for unique_together violation before saving
            if models.ExpectedMonthlyCategoryTotal.objects.filter(
                category=budget_row.category, month=current_month
            ).exists():
                form.add_error(
                    "category",
                    "A budget row for this category already exists in this month.",
                )
            else:
                budget_row.save()
                return redirect(
                    "{}?month={}".format(reverse("budget"), current_month.slug)
                )

        # Put the form (with errors) back in the right slot
        if form:
            if form_type == models.Category.TYPE_EXPENSE:
                expense_form = form
            elif form_type == models.Category.TYPE_EARNING:
                earning_form = form

    # Fetch all rows once and split in Python to avoid extra DB queries
    all_rows = list(
        models.ExpectedMonthlyCategoryTotal.objects.filter(
            month=current_month
        ).select_related("category")
    )
    earning_rows = [r for r in all_rows if r.category.type_cat == models.Category.TYPE_EARNING]
    expense_rows = [r for r in all_rows if r.category.type_cat == models.Category.TYPE_EXPENSE]
    earning_total = sum(r.amount for r in earning_rows)
    expense_total = sum(r.amount for r in expense_rows)

    context = {
        "earning_rows": earning_rows,
        "expense_rows": expense_rows,
        "earning_total": earning_total,
        "expense_total": expense_total,
        "total": earning_total - expense_total,
        "months": models.Month.objects.all(),
        "active_month": current_month,
        "expense_form": expense_form,
        "earning_form": earning_form,
        "expense_type_constant": models.Category.TYPE_EXPENSE,
        "earning_type_constant": models.Category.TYPE_EARNING,
    }
    return render(request, "occurrence/budget.html", context)


@require_http_methods(["GET", "POST"])
def edit_budget_row(request, id):
    """Edit a budget row."""
    row = get_object_or_404(models.ExpectedMonthlyCategoryTotal, pk=id)
    original_category_id = row.category_id

    if request.method == "POST":
        form = forms.ExpectedMonthlyCategoryTotalForm(request.POST, instance=row)
        if form.is_valid():
            # Check for unique_together violation if category changed
            if (
                form.cleaned_data["category"].id != original_category_id
                and models.ExpectedMonthlyCategoryTotal.objects.filter(
                    category=form.cleaned_data["category"], month=row.month
                ).exists()
            ):
                form.add_error(
                    "category",
                    "A budget row for this category already exists in this month.",
                )
            else:
                form.save()
                return redirect(
                    "{}?month={}".format(reverse("budget"), row.month.slug)
                )
    else:
        form = forms.ExpectedMonthlyCategoryTotalForm(instance=row)

    context = {"form": form, "row": row}
    return render(request, "occurrence/edit_budget_row.html", context)


@require_http_methods(["POST"])
def delete_budget_row(request, id):
    """Delete a budget row."""
    row = get_object_or_404(models.ExpectedMonthlyCategoryTotal, pk=id)
    month_slug = row.month.slug
    row.delete()
    return redirect("{}?month={}".format(reverse("budget"), month_slug))


@require_http_methods(["POST"])
def copy_budget(request):
    """Copy all budget rows from a source month to the target month."""
    source_month = get_object_or_404(
        models.Month, slug=request.POST.get("source_month")
    )
    target_month = get_object_or_404(
        models.Month, slug=request.POST.get("target_month")
    )

    source_rows = models.ExpectedMonthlyCategoryTotal.objects.filter(
        month=source_month
    ).select_related("category")

    if not source_rows.exists():
        messages.info(request, "The source month has no budget rows to copy.")
        return redirect("{}?month={}".format(reverse("budget"), target_month.slug))

    # Check for conflicts
    existing_categories = set(
        models.ExpectedMonthlyCategoryTotal.objects.filter(
            month=target_month
        ).values_list("category_id", flat=True)
    )
    conflicts = [row for row in source_rows if row.category_id in existing_categories]

    if conflicts:
        for row in conflicts:
            messages.error(
                request,
                "Category '{}' already has a budget row in {}.".format(
                    row.category.name, target_month.name
                ),
            )
        return redirect("{}?month={}".format(reverse("budget"), target_month.slug))

    # No conflicts — copy all rows
    new_rows = [
        models.ExpectedMonthlyCategoryTotal(
            category=row.category,
            month=target_month,
            amount=row.amount,
        )
        for row in source_rows
    ]
    models.ExpectedMonthlyCategoryTotal.objects.bulk_create(new_rows)
    messages.success(
        request,
        "{} budget row(s) copied from {} to {}.".format(
            len(new_rows), source_month.name, target_month.name
        ),
    )
    return redirect("{}?month={}".format(reverse("budget"), target_month.slug))


@require_http_methods(["GET"])
def statistics_chart_view(request):
    all_statistics = models.Statistic.objects.all()
    all_months = models.Month.objects.order_by("year", "month")

    statistic_slug = request.GET.get("statistic")
    start_month_slug = request.GET.get("start_month")
    end_month_slug = request.GET.get("end_month")

    statistic = None
    chart_data = []

    if statistic_slug and start_month_slug and end_month_slug:
        statistic = get_object_or_404(models.Statistic, slug=statistic_slug)
        start_month = get_object_or_404(models.Month, slug=start_month_slug)
        end_month = get_object_or_404(models.Month, slug=end_month_slug)

        months_in_range = models.Month.objects.filter(
            Q(year__gt=start_month.year) |
            Q(year=start_month.year, month__gte=start_month.month)
        ).filter(
            Q(year__lt=end_month.year) |
            Q(year=end_month.year, month__lte=end_month.month)
        )
        monthly_stats = models.MonthlyStatistic.objects.filter(
            statistic=statistic,
            month__in=months_in_range,
        ).select_related("month").order_by("month__year", "month__month")

        chart_data = [
            {"month": str(ms.month), "amount": float(ms.amount)}
            for ms in monthly_stats
        ]

    context = {
        "all_statistics": all_statistics,
        "all_months": all_months,
        "selected_statistic": statistic,
        "chart_data": chart_data,
    }
    return render(request, "occurrence/statistics.html", context)


@require_http_methods(["GET", "POST"])
def copy_transactions(request):
    """Copy transactions to a new date."""
    # Get the parameters from the request.
    if request.method == "GET":
        request_data = request.GET
    elif request.method == "POST":
        request_data = request.POST
    transaction_type = request_data.get("transaction_type", "")
    request_transaction_ids = request_data.getlist("selected_transactions", [])

    selected_transaction_ids = []
    try:
        for id in request_transaction_ids:
            selected_transaction_ids.append(int(id))
    except (ValueError, TypeError):
        context = {"errors": ["The selected transaction ids must be integers."]}
        return render(request, "occurrence/copy_transactions.html", context)

    if transaction_type == models.Category.TYPE_EXPENSE:
        transactions = models.ExpenseTransaction.objects.filter(
            id__in=selected_transaction_ids
        )
    elif transaction_type == models.Category.TYPE_EARNING:
        transactions = models.EarningTransaction.objects.filter(
            id__in=selected_transaction_ids
        )
    else:
        error = (
            f"You must choose a valid transaction_type (either '{models.Category.TYPE_EXPENSE}' "
            f"or '{models.Category.TYPE_EARNING}')."
        )
        context = {"errors": [error]}
        return render(request, "occurrence/copy_transactions.html", context)

    if len(request_transaction_ids) != transactions.count():
        error = "One or more of the selected transactions does not exist."
        context = {"errors": [error]}
        return render(request, "occurrence/copy_transactions.html", context)

    if request.method == "GET":
        # For GET requests, render a page with the relevant transaction data.
        context = {
            "transactions": transactions,
            "transaction_type": transaction_type,
            "errors": [],
        }
        return render(request, "occurrence/copy_transactions.html", context)
    else:
        # For POST requests, create new transactions, based on the chosen transactions' data.
        new_date = request.POST.get("date")
        if new_date:
            new_date_obj = parse_date(new_date)
        if not new_date_obj:
            error = f"You must choose a date in the appropriate format. '{new_date}' is not valid."
            context = {"errors": [error]}
            return render(request, "occurrence/copy_transactions.html", context)

        # Determine the Month for the selected date.
        month = utils.get_or_create_month_for_date_obj(new_date_obj)

        # Create new transactions, based on the chosen transactions' data.
        if transaction_type == models.Category.TYPE_EXPENSE:
            TransactionModel = models.ExpenseTransaction
        elif transaction_type == models.Category.TYPE_EARNING:
            TransactionModel = models.EarningTransaction
        new_transactions = []
        for transaction in transactions:
            new_transactions.append(
                TransactionModel(
                    category=transaction.category,
                    title=transaction.title,
                    slug=utils.create_unique_slug_for_transaction(transaction),
                    date=new_date_obj,
                    amount=transaction.amount,
                    month=month,
                    description=transaction.description,
                )
            )
        num_transactions_created = TransactionModel.objects.bulk_create(
            new_transactions
        )

        messages.success(
            request, f"{len(num_transactions_created)} transaction(s) copied."
        )
        return redirect("transactions")
