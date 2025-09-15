import os

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from data_tools.models import CSVImport
from data_tools.utils import ingest_csv
from occurrence.models import (
    Category,
    Month,
    ExpenseTransaction,
    EarningTransaction,
)


class IngestCSVTest(TestCase):
    def setUp(self):
        # Create categories for testing
        self.category_uncategorized_expense, _ = Category.objects.get_or_create(
            name="Uncategorized Expense",
            type_cat=Category.TYPE_EXPENSE,
            slug="uncategorized-expense",
        )
        self.category_uncategorized_earning, _ = Category.objects.get_or_create(
            name="Uncategorized Earning",
            type_cat=Category.TYPE_EARNING,
            slug="uncategorized-earning",
        )
        self.category_food_and_drink, _ = Category.objects.get_or_create(
            name="Food & Drink",
            type_cat=Category.TYPE_EXPENSE,
            slug="food-drink",
        )
        # Create a CSVImport instance
        self.csv_import = CSVImport.objects.create()

    def test_successful_ingestion(self):
        # Set the (valid) example.csv file as the self.csv_import's file.
        csv_file_path = os.path.join(os.path.dirname(__file__), "example.csv")
        with open(csv_file_path, "rb") as the_file:
            self.csv_import.file = SimpleUploadedFile(
                "example.csv", the_file.read(), content_type="text/csv"
            )
            self.csv_import.save()

        # Currently, there are no Months.
        self.assertEqual(Month.objects.count(), 0)

        # Ingest the CSV file
        count_transactions_created, errors = ingest_csv(self.csv_import)

        # Check the returned values.
        self.assertEqual(count_transactions_created, 3)
        self.assertEqual(errors, [])
        # Check that the transactions were created
        self.assertEqual(ExpenseTransaction.objects.count(), 2)
        self.assertEqual(EarningTransaction.objects.count(), 1)
        self.assertEqual(
            ExpenseTransaction.objects.filter(title="Test Restaurant 1").count(), 1
        )
        self.assertEqual(
            ExpenseTransaction.objects.filter(title="Test Restaurant 2").count(), 1
        )
        self.assertEqual(
            EarningTransaction.objects.filter(title="Company A").count(), 1
        )

        # Check amounts are positive
        for transaction in ExpenseTransaction.objects.all():
            self.assertGreater(transaction.amount, 0)

        for transaction in ExpenseTransaction.objects.all():
            self.assertGreater(transaction.amount, 0)

        # All transactions were put into the appropriate category.
        self.assertEqual(
            ExpenseTransaction.objects.filter(
                category=self.category_food_and_drink
            ).count(),
            1,
        )
        self.assertEqual(
            ExpenseTransaction.objects.filter(
                category=self.category_uncategorized_expense,
            ).count(),
            1,
        )
        self.assertEqual(
            EarningTransaction.objects.filter(
                category=self.category_uncategorized_earning
            ).count(),
            1,
        )
        # Check that a Month was created.
        self.assertEqual(Month.objects.count(), 1)
        self.assertEqual(
            Month.objects.filter(name="July, 2025", month=7, year=2025).count(),
            1,
        )

    def test_invalid_date_format(self):
        # Set the (invalid) example_invalid_date.csv file as the self.csv_import's file.
        # Path to the invalid date format CSV file
        invalid_csv_file_path = os.path.join(
            os.path.dirname(__file__), "example_invalid_date.csv"
        )
        with open(invalid_csv_file_path, "rb") as the_file:
            self.csv_import.file = SimpleUploadedFile(
                "example.csv", the_file.read(), content_type="text/csv"
            )
            self.csv_import.save()

        # Ingest the CSV file
        count_transactions_created, errors = ingest_csv(self.csv_import)

        # Check the returned values.
        self.assertEqual(count_transactions_created, 0)
        expected_error_msg = (
            "Invalid date format for row: "
            "{'Transaction Date': 'July 2 2025', 'Post Date': 'July 3 2025', "
            "'Description': 'Test Restaurant 2', 'Category': 'Food & Drink', "
            "'Type': 'Sale', 'Amount': '11.91', 'Memo': ''}. "
            "Skipping."
        )
        self.assertEqual(errors, [expected_error_msg])
        # Check that no transactions were created
        self.assertEqual(ExpenseTransaction.objects.count(), 0)
        self.assertEqual(EarningTransaction.objects.count(), 0)
        # Check that no Months were created.
        self.assertEqual(Month.objects.count(), 0)

    def test_duplicate_transaction(self):
        # Set the (valid) example.csv file as the self.csv_import's file.
        csv_file_path = os.path.join(os.path.dirname(__file__), "example.csv")
        with open(csv_file_path, "rb") as the_file:
            self.csv_import.file = SimpleUploadedFile(
                "example.csv", the_file.read(), content_type="text/csv"
            )
            self.csv_import.save()

        # Ingest the CSV file several times.
        count_transactions_created1, errors1 = ingest_csv(self.csv_import)
        count_transactions_created2, errors2 = ingest_csv(self.csv_import)

        # Check the returned values.
        self.assertEqual(count_transactions_created1, 3)
        self.assertEqual(errors1, [])
        self.assertEqual(count_transactions_created2, 0)
        self.assertEqual(errors2, [])
        # Check that the duplicate transactions were not created.
        self.assertEqual(ExpenseTransaction.objects.count(), 2)
        self.assertEqual(EarningTransaction.objects.count(), 1)
        self.assertEqual(EarningTransaction.objects.count(), 1)
