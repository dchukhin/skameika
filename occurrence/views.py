from datetime import date

from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.text import slugify

from . import forms, models


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
    # Calculate the expense totals for this month
    expense_categories = models.Category.objects.filter(
        type_cat=models.Category.TYPE_EXPENSE,
        expensetransaction__month=month
    ).annotate(
        total=Sum('expensetransaction__amount')
    )
    expense_total = expense_categories.aggregate(grand_total=Sum('total'))['grand_total'] or 0
    # Calculate the earning totals for this month
    earning_categories = models.Category.objects.filter(
        type_cat=models.Category.TYPE_INCOME,
        earningtransaction__month=month
    ).annotate(
        total=Sum('earningtransaction__amount')
    )
    earning_total = earning_categories.aggregate(grand_total=Sum('total'))['grand_total'] or 0

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
