import os
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from data_tools.models import CategoryMapping, CSVImport, TitleMapping
from data_tools.utils import ingest_csv
from occurrence.models import (
    Category,
    EarningTransaction,
    ExpenseTransaction,
    Month,
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
        self.category_other, _ = Category.objects.get_or_create(
            name="Other",
            type_cat=Category.TYPE_EXPENSE,
            slug="other",
        )
        # Create a CSVImport instance
        self.csv_import = CSVImport.objects.create()

    def _set_csv_file(self, filename):
        """Set the named fixture file as self.csv_import's file."""
        csv_file_path = os.path.join(os.path.dirname(__file__), filename)
        with open(csv_file_path, "rb") as the_file:
            self.csv_import.file = SimpleUploadedFile(
                filename, the_file.read(), content_type="text/csv"
            )
            self.csv_import.save()

    def test_successful_ingestion(self):
        # Set the (valid) example.csv file as the self.csv_import's file.
        self._set_csv_file("example.csv")

        # Currently, there are no Months.
        self.assertEqual(Month.objects.count(), 0)

        # Ingest the CSV file
        count_transactions_created, errors = ingest_csv(self.csv_import)

        # Check the returned values.
        self.assertEqual(count_transactions_created, 3)
        self.assertEqual(errors, [])

        # Check that the CSVImport object was updated with row counts
        self.csv_import.refresh_from_db()
        self.assertEqual(self.csv_import.rows_created, 3)
        self.assertEqual(self.csv_import.rows_skipped, 0)
        # Check that the transactions were created
        self.assertEqual(ExpenseTransaction.objects.count(), 2)
        self.assertEqual(EarningTransaction.objects.count(), 1)
        self.assertEqual(ExpenseTransaction.objects.filter(title="Test Restaurant 1").count(), 1)
        self.assertEqual(ExpenseTransaction.objects.filter(title="Test Restaurant 2").count(), 1)
        self.assertEqual(EarningTransaction.objects.filter(title="Company A").count(), 1)

        # Check amounts are positive
        for transaction in ExpenseTransaction.objects.all():
            self.assertGreater(transaction.amount, 0)

        for transaction in ExpenseTransaction.objects.all():
            self.assertGreater(transaction.amount, 0)

        # All transactions were put into the appropriate category.
        self.assertEqual(
            ExpenseTransaction.objects.filter(category=self.category_food_and_drink).count(),
            1,
        )
        self.assertEqual(
            ExpenseTransaction.objects.filter(
                category=self.category_uncategorized_expense,
            ).count(),
            1,
        )
        self.assertEqual(
            EarningTransaction.objects.filter(category=self.category_uncategorized_earning).count(),
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
        self._set_csv_file("example_invalid_date.csv")

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

        # Check that the CSVImport object was updated with row counts
        self.csv_import.refresh_from_db()
        self.assertEqual(self.csv_import.rows_created, 0)
        self.assertEqual(self.csv_import.rows_skipped, 1)
        # Check that no transactions were created
        self.assertEqual(ExpenseTransaction.objects.count(), 0)
        self.assertEqual(EarningTransaction.objects.count(), 0)
        # Check that no Months were created.
        self.assertEqual(Month.objects.count(), 0)

    def test_duplicate_transaction(self):
        # Set the (valid) example.csv file as the self.csv_import's file.
        self._set_csv_file("example.csv")

        # Ingest the CSV file several times.
        count_transactions_created1, errors1 = ingest_csv(self.csv_import)
        count_transactions_created2, errors2 = ingest_csv(self.csv_import)

        # Check the returned values.
        self.assertEqual(count_transactions_created1, 3)
        self.assertEqual(errors1, [])
        self.assertEqual(count_transactions_created2, 0)
        self.assertEqual(errors2, [])

        # Check that the CSVImport object was updated with row counts from the second run
        self.csv_import.refresh_from_db()
        self.assertEqual(
            self.csv_import.rows_created, 0
        )  # No new transactions created on second run
        self.assertEqual(self.csv_import.rows_skipped, 3)  # All 3 rows were skipped as duplicates
        # Check that the duplicate transactions were not created.
        self.assertEqual(ExpenseTransaction.objects.count(), 2)
        self.assertEqual(EarningTransaction.objects.count(), 1)

    def test_title_mapping(self):
        """Test that title mappings are correctly applied during CSV ingestion."""
        # Create title mappings
        TitleMapping.objects.create(
            source_title="Test Restaurant 1", canonical_title="Restaurant One"
        )
        TitleMapping.objects.create(
            source_title="Test Restaurant 2", canonical_title="Restaurant Two"
        )

        # Set the (valid) example.csv file as the self.csv_import's file.
        self._set_csv_file("example.csv")

        # Ingest the CSV file
        count_transactions_created, errors = ingest_csv(self.csv_import)

        # Check the returned values
        self.assertEqual(count_transactions_created, 3)
        self.assertEqual(errors, [])

        # Check that the CSVImport object was updated with row counts
        self.csv_import.refresh_from_db()
        self.assertEqual(self.csv_import.rows_created, 3)
        self.assertEqual(self.csv_import.rows_skipped, 0)

        # Check that transactions were created with the mapped titles
        self.assertEqual(ExpenseTransaction.objects.count(), 2)
        self.assertEqual(EarningTransaction.objects.count(), 1)

        # Verify the mapped titles are used
        self.assertTrue(ExpenseTransaction.objects.filter(title="Restaurant One").exists())
        self.assertTrue(ExpenseTransaction.objects.filter(title="Restaurant Two").exists())

        # Verify original titles are NOT used
        self.assertFalse(ExpenseTransaction.objects.filter(title="Test Restaurant 1").exists())
        self.assertFalse(ExpenseTransaction.objects.filter(title="Test Restaurant 2").exists())

        # The earning transaction (Company A) should remain unchanged since no mapping exists
        self.assertTrue(EarningTransaction.objects.filter(title="Company A").exists())

    def test_category_mapping(self):
        """CategoryMapping overrides the CSV Category column for matching descriptions."""
        # Map "Test Restaurant 1" (CSV category: "Food & Drink") to Other
        CategoryMapping.objects.create(
            source_title="Test Restaurant 1",
            category=self.category_other,
        )
        self._set_csv_file("example.csv")

        count_transactions_created, errors = ingest_csv(self.csv_import)

        self.assertEqual(count_transactions_created, 3)
        self.assertEqual(errors, [])

        # "Test Restaurant 1" uses CategoryMapping, not the CSV column
        restaurant_1 = ExpenseTransaction.objects.get(title="Test Restaurant 1")
        self.assertEqual(restaurant_1.category, self.category_other)

        # "Test Restaurant 2" has no CategoryMapping — uses the CSV column fallback
        restaurant_2 = ExpenseTransaction.objects.get(title="Test Restaurant 2")
        self.assertEqual(restaurant_2.category, self.category_uncategorized_expense)

    def test_category_mapping_no_match(self):
        """Rows without a CategoryMapping entry use the CSV Category column as before."""
        self._set_csv_file("example.csv")

        count_transactions_created, errors = ingest_csv(self.csv_import)

        self.assertEqual(count_transactions_created, 3)
        self.assertEqual(errors, [])

        # Unchanged: "Test Restaurant 1" gets food_and_drink from CSV column
        restaurant_1 = ExpenseTransaction.objects.get(title="Test Restaurant 1")
        self.assertEqual(restaurant_1.category, self.category_food_and_drink)

    def test_category_mapping_uses_mapped_title(self):
        """CategoryMapping is matched against the mapped title, not the original description."""
        # TitleMapping renames "Test Restaurant 1" → "Restaurant One"
        TitleMapping.objects.create(
            source_title="Test Restaurant 1",
            canonical_title="Restaurant One",
        )
        # CategoryMapping on the canonical title "Restaurant One" → other
        CategoryMapping.objects.create(
            source_title="Restaurant One",
            category=self.category_other,
        )

        self._set_csv_file("example.csv")

        count_transactions_created, errors = ingest_csv(self.csv_import)

        self.assertEqual(count_transactions_created, 3)
        self.assertEqual(errors, [])

        # "Restaurant One" (mapped from "Test Restaurant 1") should use the CategoryMapping
        restaurant_1 = ExpenseTransaction.objects.get(title="Restaurant One")
        self.assertEqual(restaurant_1.category, self.category_other)

    def test_category_mapping_on_original_title_ignored_when_title_mapping_exists(self):
        """A CategoryMapping keyed on the original description has no effect when a
        TitleMapping renames that description first."""
        TitleMapping.objects.create(
            source_title="Test Restaurant 1",
            canonical_title="Restaurant One",
        )
        # CategoryMapping uses the *original* description — should NOT match after renaming
        CategoryMapping.objects.create(
            source_title="Test Restaurant 1",
            category=self.category_other,
        )

        self._set_csv_file("example.csv")

        count_transactions_created, errors = ingest_csv(self.csv_import)

        self.assertEqual(count_transactions_created, 3)
        self.assertEqual(errors, [])

        # CategoryMapping on the original title is ignored; falls back to the CSV column
        restaurant_1 = ExpenseTransaction.objects.get(title="Restaurant One")
        self.assertEqual(restaurant_1.category, self.category_food_and_drink)

    def test_ingest_csv_reuses_existing_month_with_blank_slug(self):
        """
        If a Month for a transaction's year/month already exists but has a
        blank slug, ingesting a CSV with a transaction dated in that month
        reuses the existing Month rather than creating a second one.
        """
        existing_month = Month.objects.create(year=2025, month=7, name="July, 2025", slug="")

        self._set_csv_file("example.csv")

        ingest_csv(self.csv_import)

        months = Month.objects.filter(year=2025, month=7)
        self.assertEqual(months.count(), 1)
        self.assertEqual(months.get().pk, existing_month.pk)

    def test_long_description_creates_transaction(self):
        """
        A Description that slugifies to more than 50 characters imports
        successfully instead of failing with a database error.
        """
        self._set_csv_file("example_long_description.csv")

        count_transactions_created, errors = ingest_csv(self.csv_import)

        self.assertEqual(errors, [])
        self.assertEqual(count_transactions_created, 1)
        transaction = ExpenseTransaction.objects.get()
        self.assertEqual(
            transaction.title,
            "long description about the transaction that continues for many characters and words",
        )
        self.assertLessEqual(len(transaction.slug), 255)
        self.assertTrue(
            transaction.slug.startswith(
                "long-description-about-the-transaction-that-continues-for-many-characters-and-words"
            )
        )

    def test_reimport_same_rows_different_amounts(self):
        """
        A second import with the same descriptions, dates, and row positions
        but different amounts (e.g. recurring charges) creates new
        transactions instead of colliding on identical slugs.
        """
        self._set_csv_file("example.csv")
        count1, errors1 = ingest_csv(self.csv_import)
        self.assertEqual((count1, errors1), (3, []))
        self.assertEqual(ExpenseTransaction.objects.count(), 2)
        self.assertEqual(
            set(ExpenseTransaction.objects.values_list("amount", flat=True)),
            set([Decimal("9.02"), Decimal("11.91")]),
        )
        self.assertEqual(EarningTransaction.objects.count(), 1)
        self.assertEqual(
            set(EarningTransaction.objects.values_list("amount", flat=True)),
            set([Decimal("-11.91")]),
        )

        # Same rows with different amounts, in a second import.
        csv_file_path = os.path.join(os.path.dirname(__file__), "example.csv")
        with open(csv_file_path) as the_file:
            modified_csv = the_file.read().replace("9.02", "10.03").replace("11.91", "12.92")
        second_import = CSVImport.objects.create(
            file=SimpleUploadedFile("example2.csv", modified_csv.encode(), content_type="text/csv")
        )

        count2, errors2 = ingest_csv(second_import)

        self.assertEqual(errors2, [])
        self.assertEqual(count2, 3)
        self.assertEqual(ExpenseTransaction.objects.count(), 4)
        self.assertEqual(
            set(ExpenseTransaction.objects.values_list("amount", flat=True)),
            set([Decimal("9.02"), Decimal("11.91"), Decimal("10.03"), Decimal("12.92")]),
        )
        self.assertEqual(EarningTransaction.objects.count(), 2)
        self.assertEqual(
            set(EarningTransaction.objects.values_list("amount", flat=True)),
            set([Decimal("-11.91"), Decimal("-12.92")]),
        )
