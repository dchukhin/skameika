from datetime import date

from django.db.models import DecimalField, F, Sum, Value
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.text import slugify
from django.views.decorators.http import require_http_methods

from . import forms, models, utils


def transactions(request, *args, **kwargs):
    """Show all current transactions."""
    # Get the current_month, either from the request kwargs, or use the today's month
    if request.GET.get('month'):
        current_month = get_object_or_404(
            models.Month.objects.all(),
            name=request.GET.get('month')
        )
    else:
        current_month = models.Month.objects.get_or_create(
            year=date.today().year,
            month=date.today().month,
            name=date.today().strftime('%B, %Y'),
        )[0]
    expense_transactions = models.ExpenseTransaction.objects.filter(month=current_month)
    earning_transactions = models.EarningTransaction.objects.filter(month=current_month)

    context = {
        'expense_transactions': expense_transactions,
        'earning_transactions': earning_transactions,
        'expense_form': forms.ExpenseTransactionForm(),
        'earning_form': forms.EarningTransactionForm(),
        'current_month': current_month,
        'months': models.Month.objects.all(),
    }
    if request.method == 'POST':
        # Is this for an expense, or an earning?
        if request.POST.get('form_type') == 'expense':
            # Use the ExpenseTransactionForm for expense POSTs
            form = forms.ExpenseTransactionForm(request.POST)
        elif request.POST.get('form_type') == 'earning':
            # Use the EarningTransactionForm for earning POSTs
            form = forms.EarningTransactionForm(request.POST)

        # If the form is valid, then save the form
        if form.is_valid():
            form.save()
        else:
            # The form is not valid, so return the invalid form to the template
            context['expense_form'] = form
    return render(request, 'occurrence/transactions.html', context)


@require_http_methods(["GET"])
def totals(request, *args, **kwargs):
    """Show totals (for transactions) by category."""
    month_slug = request.GET.get('month')
    # If the user did not provide a month_slug, then redirect to the totals
    # for the current month
    if not month_slug:
        current_month = models.Month.objects.get_or_create(
            year=date.today().year,
            month=date.today().month,
            name=date.today().strftime('%B, %Y'),
            slug=slugify(date.today().strftime('%B, %Y')),
        )[0]
        return redirect('{}?month={}'.format(reverse('totals'), current_month.slug))

    month = get_object_or_404(models.Month.objects.all(), slug=month_slug)

    # Get the expense totals for this month
    expense_categories, expense_total = utils.get_transactions_regular_totals(
        month,
        type_cat=models.Category.TYPE_EXPENSE,
    )
    # Get the earning totals for this month
    earning_categories, earning_total = utils.get_transactions_regular_totals(
        month,
        type_cat=models.Category.TYPE_EARNING,
    )

    context = {
        'expense_categories': expense_categories,
        'expense_total': expense_total,
        'earning_categories': earning_categories,
        'earning_total': earning_total,
        'total': earning_total - expense_total,
        'months': models.Month.objects.all(),
        'active_month': month,
    }
    return render(request, 'occurrence/totals.html', context)


@require_http_methods(["GET"])
def running_total_categories(request):
    """The view for Categories that have a running total, rather than the regular total."""
    categories = models.Category.objects.filter(
        total_type=models.Category.TOTAL_TYPE_RUNNING
    ).annotate(
        total=Sum(
            F('expensetransaction__amount') * Value('-1'),
            output_field=DecimalField()
        ),
    )
    # For each Category, attach a queryset of ExpenseTransactions that have a
    # running_total_amount fiels
    for category in categories:
        category.expense_transactions = utils.get_expensetransactions_running_totals(category)

    context = {
        'categories': categories
    }
    return render(request, 'occurrence/running_totals.html', context)


@require_http_methods(["GET", "POST"])
def edit_transaction(request, type_cat, id):
    """Edit a transaction."""
    # Attempt to find the transaction, based on the type_cat
    if type_cat == models.Category.TYPE_EXPENSE:
        transaction = get_object_or_404(
            models.ExpenseTransaction.objects.all(),
            pk=id
        )
    elif type_cat == models.Category.TYPE_EARNING:
        transaction = get_object_or_404(
            models.EarningTransaction.objects.all(),
            pk=id
        )
    else:
        raise Http404('Category type not recognized')

    if request.method == "POST":
        if type_cat == models.Category.TYPE_EXPENSE:
            form = forms.ExpenseTransactionForm(request.POST, instance=transaction)
        elif type_cat == models.Category.TYPE_EARNING:
            form = forms.EarningTransactionForm(request.POST, instance=transaction)
        # If the form is valid, save the object
        if form.is_valid():
            form.save()
            # Redirect the user to the transactions view for the month that this
            # transaction is in
            return redirect('{}?month={}'.format(reverse('transactions'), transaction.month.name))
    else:
        if type_cat == models.Category.TYPE_EXPENSE:
            form = forms.ExpenseTransactionForm(instance=transaction)
        elif type_cat == models.Category.TYPE_EARNING:
            form = forms.EarningTransactionForm(instance=transaction)
    context = {'form': form, 'transaction': transaction, 'type_cat': type_cat}
    return render(request, 'occurrence/edit_transaction.html', context)
