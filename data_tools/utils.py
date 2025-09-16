import csv
import logging
from datetime import datetime
from django.core.exceptions import ObjectDoesNotExist
from django.utils.text import slugify

from data_tools.models import CSVImport, TitleMapping
from occurrence.models import ExpenseTransaction, EarningTransaction, Category, Month


logger = logging.getLogger(__name__)


def get_mapped_title(description, title_mappings):
    """
    Get the canonical title for a transaction description using a pre-loaded mapping dictionary.

    Args:
        description (str): The original transaction description.
        title_mappings (dict): Dictionary mapping source_title -> canonical_title.

    Returns:
        str: The canonical title if a mapping exists, otherwise the original description.
    """
    return title_mappings.get(description, description)


def parse_date(date_string):
    """
    Convert a date string into a date object.

    Supports the following formats:
    - "YYYY-MM-DD"
    - "MM/DD/YYYY"

    Args:
        date_string (str): The date string to convert.

    Returns:
        date: The corresponding date object.

    Raises:
        ValueError: If the date string is in an invalid format.
    """
    for fmt in ("%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(date_string, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Invalid date format: {date_string}")


def ingest_csv(csv_import):
    """
    Ingest a CSV file. See example.csv for an example.
    """
    TYPE_EARNING = "earning"
    TYPE_EXPENSE = "expense"

    # Load all title mappings into a dictionary for efficient lookup
    title_mappings = dict(
        TitleMapping.objects.values_list("source_title", "canonical_title")
    )

    expense_transactions = []
    earning_transactions = []
    errors = []
    rows_skipped = 0

    with csv_import.file.open(mode="r") as csvfile:
        reader = csv.DictReader(csvfile)
        for index, row in enumerate(reader):
            amount = float(row["Amount"])

            # Convert the date string to a date object
            try:
                transaction_date = parse_date(row["Transaction Date"])
            except ValueError:
                error_msg = f"Invalid date format for row: {row}. Skipping."
                errors.append(error_msg)
                logger.error(error_msg)
                rows_skipped += 1
                continue
            else:
                month, _ = Month.objects.get_or_create(
                    month=transaction_date.month,
                    year=transaction_date.year,
                    name=transaction_date.strftime("%B, %Y"),
                    slug=slugify(transaction_date.strftime("%B, %Y")),
                )

            transaction_type = row["Type"].strip().lower()

            if transaction_type.lower() == "income":
                expense_or_earning = TYPE_EARNING
            else:
                expense_or_earning = TYPE_EXPENSE

            # Determine the category based on the provided name
            default_category_name = "Uncategorized"
            category = None
            try:
                category = Category.objects.get(name__iexact=row["Category"])
            except ObjectDoesNotExist:
                categories = Category.objects.filter(
                    name__icontains=default_category_name
                )
                if categories.count() > 1:
                    category = categories.filter(
                        name__icontains=expense_or_earning
                    ).first()
                if not category:
                    category = categories.first()

            # Get the mapped title for this transaction
            mapped_title = get_mapped_title(row["Description"], title_mappings)

            # Check if the transaction already exists based on title, amount, and date
            if transaction_type.lower() == "income":
                existing_transaction = EarningTransaction.objects.filter(
                    title=mapped_title, amount=amount, date=transaction_date
                ).first()
                if existing_transaction:
                    logger.info(
                        f"Transaction '{mapped_title}' already exists. Skipping."
                    )
                    rows_skipped += 1
                    continue

                # Create a new EarningTransaction
                earning_transactions.append(
                    EarningTransaction(
                        title=mapped_title,
                        slug=f"{slugify(mapped_title)}-{transaction_date.strftime('%Y-%m-%d')}-{index}",
                        amount=amount,
                        month=month,
                        category=category,
                        csv_import=csv_import,
                        pending=True,
                        date=transaction_date,
                    )
                )
            else:
                existing_transaction = ExpenseTransaction.objects.filter(
                    title=mapped_title, amount=amount, date=transaction_date
                ).first()
                if existing_transaction:
                    logger.info(
                        f"Transaction '{mapped_title}' already exists. Skipping."
                    )
                    rows_skipped += 1
                    continue

                # Create a new ExpenseTransaction
                expense_transactions.append(
                    ExpenseTransaction(
                        title=mapped_title,
                        slug=f"{slugify(mapped_title)}-{transaction_date.strftime('%Y-%m-%d')}-{index}",
                        amount=amount,
                        month=month,
                        category=category,
                        csv_import=csv_import,
                        pending=True,
                        date=transaction_date,
                    )
                )

    count_transactions_created = 0
    if not errors:
        expense_transactions_created = ExpenseTransaction.objects.bulk_create(
            expense_transactions
        )
        earning_transactions_created = EarningTransaction.objects.bulk_create(
            earning_transactions
        )
        count_transactions_created = len(expense_transactions_created) + len(
            earning_transactions_created
        )

    # Update the CSVImport object with the row counts
    csv_import.rows_created = count_transactions_created
    csv_import.rows_skipped = rows_skipped
    csv_import.save(update_fields=["rows_created", "rows_skipped"])

    return count_transactions_created, errors
