from django import forms

from . import models


class ExpenseTransactionForm(forms.ModelForm):
    class Meta:
        model = models.ExpenseTransaction
        exclude = ["slug", "month"]


class EarningTransactionForm(forms.ModelForm):
    class Meta:
        model = models.EarningTransaction
        exclude = ["slug", "month"]


class ExpectedMonthlyCategoryTotalForm(forms.ModelForm):
    class Meta:
        model = models.ExpectedMonthlyCategoryTotal
        exclude = ["month"]


class ExpenseBudgetRowForm(forms.ModelForm):
    class Meta:
        model = models.ExpectedMonthlyCategoryTotal
        exclude = ["month"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = models.Category.objects.filter(
            type_cat=models.Category.TYPE_EXPENSE
        )


class EarningBudgetRowForm(forms.ModelForm):
    class Meta:
        model = models.ExpectedMonthlyCategoryTotal
        exclude = ["month"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = models.Category.objects.filter(
            type_cat=models.Category.TYPE_EARNING
        )
