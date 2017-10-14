from django.db.models import DecimalField, F, Sum, Value

from . import models


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
