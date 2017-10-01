from datetime import date

from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.text import slugify

from . import forms, models


def transactions(request, *args, **kwargs):
    """Show all current Transactions."""
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

    context = {
        'transactions': expense_transactions,
        'form': forms.ExpenseTransactionForm(),
        'current_month': current_month,
        'months': models.Month.objects.all(),
    }
    if request.method == 'POST':
        # If this is a POST and the form is valid, then save the form
        form = forms.ExpenseTransactionForm(request.POST)
        if form.is_valid():
            form.save()
        else:
            # The form is not valid, so return the invalid form to the template
            context['form'] = form
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

    current_month = get_object_or_404(models.Month.objects.all(), slug=month_slug)
    month = get_object_or_404(models.Month.objects.all(), slug=month_slug)
    categories = models.Category.objects.filter(expensetransaction__month=month).annotate(
        total=Sum('expensetransaction__amount')
    )
    context = {
        'categories': categories,
        'months': models.Month.objects.all(),
        'current_month': current_month,
    }
    return render(request, 'occurrence/totals.html', context)
