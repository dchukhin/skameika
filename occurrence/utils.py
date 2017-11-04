from django.core.exceptions import ValidationError
from django.db.models import DecimalField, F, Sum, Value

from . import models


def get_transactions_regular_totals(month=None, type_cat=models.Category.TYPE_EXPENSE):
    """Get the totals for Categories."""
    # Raise an error if type_cat is not valid
    if type_cat not in [name for (name, label) in models.Category.TYPE_CHOICES]:
        raise ValidationError("{} is not a valid type_cat".format(type_cat))

    # Get all of the Categories of regular total_type
    categories = models.Category.objects.filter(total_type=models.Category.TOTAL_TYPE_REGULAR)

    # Filter categories by the month, and annotate the queryset with the total
    if type_cat == models.Category.TYPE_EXPENSE:
        if month:
            categories = categories.filter(expensetransaction__month=month).distinct()
        categories = categories.annotate(total=Sum('expensetransaction__amount'))
    elif type_cat == models.Category.TYPE_INCOME:
        if month:
            categories = categories.filter(earningtransaction__month=month).distinct()
        categories = categories.annotate(total=Sum('earningtransaction__amount'))

    # Aggregate to get the sum total for the transactions
    sum_total = categories.aggregate(grand_total=Sum('total'))['grand_total'] or 0

    return categories, sum_total


def get_expensetransactions_running_totals(category):
    """
    Get ExpenseTransactions for a Category that is of total_type of TOTAL_TYPE_RUNNING.

    Since these Categories will be seen as a running total, and the ExpenseTransactions
    are expenses, the transaction amounts are multiplied by -1.
    """
    # If this is not a running type Category, then just return its ExpenseTransactions
    if category.total_type != models.Category.TOTAL_TYPE_RUNNING:
        return models.ExpenseTransaction.objects.filter(
            category=category,
        )
    # This is a running type Category, so annotate the running_total_amount field
    return models.ExpenseTransaction.objects.filter(
        category=category,
    ).annotate(
        running_total_amount=Sum(
            F('amount') * Value('-1'),
            output_field=DecimalField()
        ),
    )
