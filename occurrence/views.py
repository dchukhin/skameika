from django.shortcuts import render

from . import forms, models


def transactions(request):
    """Show all current Transactions."""
    transactions = models.Transaction.objects.all()
    context = {
        'transactions': transactions,
        'form': forms.TransactionForm,
    }
    return render(request, 'occurrence/transactions.html', context)
