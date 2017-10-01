from django import forms

from . import models


class ExpenseTransactionForm(forms.ModelForm):

    class Meta:
        model = models.ExpenseTransaction
        exclude = ['slug', 'month']
