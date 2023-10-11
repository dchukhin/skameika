import uuid

from django.core.exceptions import ValidationError
from django.db.models import DecimalField, F, Sum, Value
from django.utils.text import slugify

from . import models


def get_transactions_regular_totals(month=None, type_cat=models.Category.TYPE_EXPENSE):
    """Get the totals for Categories, including children Categories."""
    # Raise an error if type_cat is not valid
    if type_cat not in [name for (name, label) in models.Category.TYPE_CHOICES]:
        raise ValidationError("{} is not a valid type_cat".format(type_cat))

    if type_cat == models.Category.TYPE_EXPENSE:
        # Get all of the ExpenseTransactions with a Cateogry of regular total_type
        transactions = models.ExpenseTransaction.objects.filter(
            category__total_type=models.Category.TOTAL_TYPE_REGULAR
        )
        if month:
            transactions = transactions.filter(month=month)
        category_totals = (
            transactions.values("category").order_by().distinct().annotate(total=Sum("amount"))
        )

        sum_total = category_totals.aggregate(grand_total=Sum("total"))["grand_total"] or 0

    elif type_cat == models.Category.TYPE_EARNING:
        # Get all of the EarningTransaction with a Cateogry of regular total_type
        transactions = models.EarningTransaction.objects.filter(
            category__total_type=models.Category.TOTAL_TYPE_REGULAR
        )
        if month:
            transactions = transactions.filter(month=month)
        category_totals = (
            transactions.values("category").order_by().distinct().annotate(total=Sum("amount"))
        )

        sum_total = category_totals.aggregate(grand_total=Sum("total"))["grand_total"] or 0

    # A list of Categories, their totals, and their children (including
    # their children's totals)
    category_dict = {}
    # Loop through the category_totals, and add categories to category_dict,
    # as well as adding their parent Category (if applicable)
    for category_data in category_totals.values(
        "category__name",
        "category__id",
        "category__order",
        "total",
        "category__parent",
        "category__parent__name",
    ).order_by("category__order", "category__name"):
        if category_data["category__parent"]:
            parent_id = category_data["category__parent"]
            if parent_id in category_dict.keys():
                # Add this total to the parent's total
                category_dict[parent_id]["total"] += category_data["total"]
                # # Add this Category to the list of children, preserving the order
                index = category_data["category__order"]
                category_dict[parent_id]["children"].insert(
                    index,
                    {
                        "name": category_data["category__name"],
                        "total": category_data["total"],
                    },
                )
            else:
                category_dict[parent_id] = {
                    "name": category_data["category__parent__name"],
                    "total": category_data["total"],
                    "children": [
                        {
                            "name": category_data["category__name"],
                            "total": category_data["total"],
                        }
                    ],
                }
        else:
            # If this Category is already in the category_dict, then just add
            # its amount to the total already there
            if category_data["category__id"] in category_dict.keys():
                category_dict[category_data["category__id"]]["total"] += category_data["total"]
            else:
                category_dict[category_data["category__id"]] = {
                    "name": category_data["category__name"],
                    "total": category_data["total"],
                    "children": [],
                }

    return category_dict, sum_total


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
        running_total_amount=Sum(F("amount") * Value("-1"), output_field=DecimalField()),
    )


def get_or_create_month_for_date_obj(date_obj):
    """Get or create a Month object for a date object."""
    try:
        month = models.Month.objects.get(month=date_obj.month, year=date_obj.year)
    except models.Month.DoesNotExist:
        # A Month for this Transaction's date does not exist, so create one
        month = models.Month.objects.create(
            month=date_obj.month,
            year=date_obj.year,
            name=date_obj.strftime("%B, %Y"),
            slug=slugify(date_obj.strftime("%B, %Y")),
        )
    return month


def create_unique_slug_for_transaction(transaction):
    # Create a slug based on title, date, and some random characters.
    return "{}-{}-{}".format(
        slugify(transaction.title),
        transaction.date.strftime("%Y-%m-%d"),
        str(uuid.uuid4()).replace("-", "")[0:10],
    )
