import csv
import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import Error, transaction
from django.utils.text import slugify

from data_tools.models import CategoryMapping, TitleMapping
from occurrence.models import (
    SLUG_GENERATED_MAX_LENGTH,
    Category,
    EarningTransaction,
    ExpenseTransaction,
    get_or_create_month_for_date_obj,
)

logger = logging.getLogger(__name__)

# The columns ingest_csv() reads from each row. Other columns are never read,
# so they are not required.
REQUIRED_COLUMNS = {"Transaction Date", "Description", "Category", "Type", "Amount"}


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


def get_mapped_category(description, category_mappings):
    """
    Get a Category override for a transaction description using a pre-loaded mapping.

    Args:
        description (str): The original CSV description.
        category_mappings (dict): Maps source_title -> Category object.

    Returns:
        Category or None: The mapped category if one exists, otherwise None.
    """
    return category_mappings.get(description, None)


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


def parse_amount(amount_string):
    """Convert a CSV Amount value into a Decimal."""
    try:
        amount = Decimal(amount_string)
    except (InvalidOperation, TypeError):
        # Decimal(None) raises TypeError rather than InvalidOperation (a
        # short row leaves the Amount cell as None).
        return None
    # "NaN" and "Infinity" parse successfully, but are not storable amounts.
    return amount if amount.is_finite() else None


def get_category_for_row(category_name, expense_or_earning):
    """Find the Category for a row, and fall back to an "Uncategorized" Category."""
    try:
        return Category.objects.get(name__iexact=category_name)
    except ObjectDoesNotExist:
        category = None
        categories = Category.objects.filter(name__icontains="Uncategorized")
        if categories.count() > 1:
            category = categories.filter(name__icontains=expense_or_earning).first()
        if not category:
            category = categories.first()
        return category


def validate_transaction(transaction_instance, row_number, description):
    """Run model-field validation on an unsaved transaction."""
    # The month and csv_import fields are excluded, because full_clean()
    # validates every ForeignKey with an existence query, and both are
    # guaranteed-saved objects set by this code.
    try:
        transaction_instance.full_clean(exclude={"month", "csv_import"}, validate_unique=False)
    except ValidationError as e:
        return [
            f"Row {row_number} ('{description[:60]}'): {field}: {' '.join(field_errors)}"
            for field, field_errors in e.message_dict.items()
        ]
    return []


def ingest_csv(csv_import):
    """
    Ingest a CSV file. See example.csv for an example.
    """
    TYPE_EARNING = "earning"
    TYPE_EXPENSE = "expense"

    # Load all title mappings into a dictionary for efficient lookup
    title_mappings = dict(TitleMapping.objects.values_list("source_title", "canonical_title"))

    # Load all category mappings into a dictionary for efficient lookup
    category_mappings = {
        m.source_title: m.category
        for m in CategoryMapping.objects.filter(category__isnull=False).select_related("category")
    }

    expense_transactions = []
    earning_transactions = []
    errors = []
    rows_skipped = 0

    with csv_import.file.open(mode="r") as csvfile:
        reader = csv.DictReader(csvfile)
        if reader.fieldnames:
            # Excel exports often prefix a UTF-8 BOM onto the
            # first header name and would make the check below claim a
            # visibly-present column is missing. FieldFile.open() accepts no
            # encoding argument, so normalize the decoded fieldnames instead
            # of opening the file with "utf-8-sig".
            reader.fieldnames = [name.removeprefix("\ufeff") for name in reader.fieldnames]
        missing_columns = REQUIRED_COLUMNS - set(reader.fieldnames or [])
        if missing_columns:
            error_msg = "File is missing required column(s): {}.".format(
                ", ".join(sorted(missing_columns))
            )
            logger.error(error_msg)
            csv_import.rows_created = 0
            csv_import.rows_skipped = 0
            csv_import.save(update_fields=["rows_created", "rows_skipped"])
            return 0, [error_msg]
        for index, row in enumerate(reader):
            amount = parse_amount(row["Amount"])
            if amount is None:
                error_msg = f"Row {index + 2}: invalid amount {repr(row['Amount'])[:80]}."
                errors.append(error_msg)
                logger.error(error_msg)
                rows_skipped += 1
                continue

            # Convert the date string to a date object
            try:
                transaction_date = parse_date(row["Transaction Date"])
            except ValueError:
                error_msg = f"Row {index + 2}: invalid date {repr(row['Transaction Date'])[:80]}."
                errors.append(error_msg)
                logger.error(error_msg)
                rows_skipped += 1
                continue
            else:
                month = get_or_create_month_for_date_obj(transaction_date)

            transaction_type = row["Type"].strip().lower()

            if transaction_type.lower() == "income":
                expense_or_earning = TYPE_EARNING
            else:
                expense_or_earning = TYPE_EXPENSE

            # Determine the category based on the provided name
            category = get_category_for_row(row["Category"], expense_or_earning)

            # Get the mapped title for this transaction
            mapped_title = get_mapped_title(row["Description"], title_mappings)

            # Override category with CategoryMapping if one exists for this description
            mapped_category = get_mapped_category(mapped_title, category_mappings)
            if mapped_category is not None:
                category = mapped_category

            # Check if the transaction already exists based on title, amount, and date
            if transaction_type.lower() == "income":
                existing_transaction = EarningTransaction.objects.filter(
                    title=mapped_title, amount=amount, date=transaction_date
                ).first()
                if existing_transaction:
                    logger.info(f"Transaction '{mapped_title}' already exists. Skipping.")
                    rows_skipped += 1
                    continue

                # Create a new EarningTransaction. The name new_transaction
                # matters, because a variable named transaction would clash with
                # the django.db.transaction module used below.
                new_transaction = EarningTransaction(
                    title=mapped_title,
                    slug=(
                        f"{slugify(mapped_title)[:SLUG_GENERATED_MAX_LENGTH]}"
                        f"-{transaction_date.strftime('%Y-%m-%d')}"
                        f"-{csv_import.pk}-{index}"
                    ),
                    amount=amount,
                    month=month,
                    category=category,
                    csv_import=csv_import,
                    pending=True,
                    date=transaction_date,
                )
                row_errors = validate_transaction(new_transaction, index + 2, row["Description"])
                if row_errors:
                    errors.extend(row_errors)
                    logger.error("; ".join(row_errors))
                    rows_skipped += 1
                    continue
                earning_transactions.append(new_transaction)
            else:
                existing_transaction = ExpenseTransaction.objects.filter(
                    title=mapped_title, amount=amount, date=transaction_date
                ).first()
                if existing_transaction:
                    logger.info(f"Transaction '{mapped_title}' already exists. Skipping.")
                    rows_skipped += 1
                    continue

                # Create a new ExpenseTransaction. The name new_transaction
                # matters, because a variable named transaction would clash with
                # the django.db.transaction module used below.
                new_transaction = ExpenseTransaction(
                    title=mapped_title,
                    slug=(
                        f"{slugify(mapped_title)[:SLUG_GENERATED_MAX_LENGTH]}"
                        f"-{transaction_date.strftime('%Y-%m-%d')}"
                        f"-{csv_import.pk}-{index}"
                    ),
                    amount=amount,
                    month=month,
                    category=category,
                    csv_import=csv_import,
                    pending=True,
                    date=transaction_date,
                )
                row_errors = validate_transaction(new_transaction, index + 2, row["Description"])
                if row_errors:
                    errors.extend(row_errors)
                    logger.error("; ".join(row_errors))
                    rows_skipped += 1
                    continue
                expense_transactions.append(new_transaction)

    count_transactions_created = 0
    if not errors:
        # atomic() allows the database transactions to either both succeed or
        # both fail, so we avoid some transactions being saved and others not
        # saved.
        try:
            with transaction.atomic():
                expense_transactions_created = ExpenseTransaction.objects.bulk_create(
                    expense_transactions
                )
                earning_transactions_created = EarningTransaction.objects.bulk_create(
                    earning_transactions
                )
            count_transactions_created = len(expense_transactions_created) + len(
                earning_transactions_created
            )
        except Error:
            # There was a database error, but give the user a generic message.
            logger.exception("bulk_create failed during CSV ingest")
            errors.append(
                "A database error prevented saving the transactions; see the server logs."
            )

    # Update the CSVImport object with the row counts
    csv_import.rows_created = count_transactions_created
    csv_import.rows_skipped = rows_skipped
    csv_import.save(update_fields=["rows_created", "rows_skipped"])

    return count_transactions_created, errors
