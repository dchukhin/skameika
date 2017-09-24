from datetime import date

from django.db.models import Sum
from django.shortcuts import get_object_or_404, render

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
    transactions = models.Transaction.objects.filter(month=current_month)

    context = {
        'transactions': transactions,
        'form': forms.TransactionForm(),
        'current_month': current_month,
        'months': models.Month.objects.all(),
    }
    if request.method == 'POST':
        # If this is a POST and the form is valid, then save the form
        form = forms.TransactionForm(request.POST)
        if form.is_valid():
            form.save()
        else:
            # The form is not valid, so return the invalid form to the template
            context['form'] = form
    return render(request, 'occurrence/transactions.html', context)


def totals(request, *args, **kwargs):
    """Show totals (for Transactions) by category."""
    if request.GET.get('month_name'):
        current_month = get_object_or_404(
            models.Month.objects.all(),
            name=request.GET.get('month_name')
        )
    else:
        current_month = models.Month.objects.get_or_create(
            year=date.today().year,
            month=date.today().month,
            name=date.today().strftime('%B, %Y'),
        )[0]

    context = {}

    month_name = request.GET.get('month_name')
    if month_name:
        month = get_object_or_404(models.Month.objects.all(), name=month_name)
        categories = models.Category.objects.filter(transaction__month=month).annotate(
            total=Sum('transaction__amount')
        )
        context = {
            'categories': categories,
        }
    context['months'] = models.Month.objects.all()
    context['current_month'] = current_month
    return render(request, 'occurrence/totals.html', context)
