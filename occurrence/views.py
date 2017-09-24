from django.shortcuts import render

from . import forms, models


def transactions(request):
    """Show all current Transactions."""
    transactions = models.Transaction.objects.all()
    context = {
        'transactions': transactions,
        'form': forms.TransactionForm()
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
