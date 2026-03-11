import uuid

from django.core.exceptions import ValidationError
from django.db.models import DecimalField, F, Sum, Value
from django.utils.text import slugify

from . import models


def get_transactions_regular_totals(
    month=None, type_cat=models.Category.TYPE_EXPENSE, budget_by_category=None
):
    """Get the totals for Categories, including children Categories.

    Args:
        month: Optional Month to filter transactions by.
        type_cat: The category type (expense or earning).
        budget_by_category: Optional dict mapping category_id to budgeted amount.
            When provided, each category entry in the returned dict will include
            a "budgeted" key. Categories that have a budget but no transactions
            will also be included with a total of 0.
    """
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

    if budget_by_category is None:
        budget_by_category = {}

    def _make_child(name, total, cat_id=None):
        entry = {"name": name, "total": total}
        if budget_by_category:
            entry["budgeted"] = budget_by_category.get(cat_id)
        return entry

    # A list of Categories, their totals, and their children (including
    # their children's totals)
    category_dict = {}
    # Track which budgeted category IDs have been handled
    seen_category_ids = set()

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
        cat_id = category_data["category__id"]
        seen_category_ids.add(cat_id)

        if category_data["category__parent"]:
            parent_id = category_data["category__parent"]
            seen_category_ids.add(parent_id)
            if parent_id in category_dict.keys():
                # Add this total to the parent's total
                category_dict[parent_id]["total"] += category_data["total"]
                # # Add this Category to the list of children, preserving the order
                index = category_data["category__order"]
                category_dict[parent_id]["children"].insert(
                    index,
                    _make_child(
                        category_data["category__name"],
                        category_data["total"],
                        cat_id,
                    ),
                )
            else:
                category_dict[parent_id] = {
                    "name": category_data["category__parent__name"],
                    "total": category_data["total"],
                    "children": [
                        _make_child(
                            category_data["category__name"],
                            category_data["total"],
                            cat_id,
                        )
                    ],
                }
                if budget_by_category:
                    category_dict[parent_id]["budgeted"] = budget_by_category.get(
                        parent_id
                    )
        else:
            # If this Category is already in the category_dict, then just add
            # its amount to the total already there
            if cat_id in category_dict.keys():
                category_dict[cat_id]["total"] += category_data["total"]
            else:
                category_dict[cat_id] = {
                    "name": category_data["category__name"],
                    "total": category_data["total"],
                    "children": [],
                }
                if budget_by_category:
                    category_dict[cat_id]["budgeted"] = budget_by_category.get(cat_id)

    # Add categories that have a budget but no transactions
    if budget_by_category:
        budget_only_cats = models.Category.objects.filter(
            id__in=set(budget_by_category.keys()) - seen_category_ids,
            total_type=models.Category.TOTAL_TYPE_REGULAR,
            type_cat=type_cat,
        ).select_related("parent")
        for cat in budget_only_cats:
            if cat.parent_id:
                if cat.parent_id not in category_dict:
                    category_dict[cat.parent_id] = {
                        "name": cat.parent.name,
                        "total": 0,
                        "budgeted": budget_by_category.get(cat.parent_id),
                        "children": [
                            _make_child(cat.name, 0, cat.id)
                        ],
                    }
                # If parent exists but this child isn't there yet, add it
                else:
                    child_names = {
                        c["name"] for c in category_dict[cat.parent_id]["children"]
                    }
                    if cat.name not in child_names:
                        category_dict[cat.parent_id]["children"].append(
                            _make_child(cat.name, 0, cat.id)
                        )
            else:
                if cat.id not in category_dict:
                    category_dict[cat.id] = {
                        "name": cat.name,
                        "total": 0,
                        "budgeted": budget_by_category.get(cat.id),
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
