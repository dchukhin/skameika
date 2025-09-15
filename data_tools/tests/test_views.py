import os

from django.test import TestCase
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.messages import get_messages

from data_tools.models import CSVImport
from occurrence.models import Category, EarningTransaction, ExpenseTransaction, Month


class UploadCSVViewTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create categories for testing
        cls.category_uncategorized_expense, _ = Category.objects.get_or_create(
            name="Uncategorized Expense",
            type_cat=Category.TYPE_EXPENSE,
            slug="uncategorized-expense",
        )
        cls.category_uncategorized_earning, _ = Category.objects.get_or_create(
            name="Uncategorized Earning",
            type_cat=Category.TYPE_EARNING,
            slug="uncategorized-earning",
        )
        cls.category_food_and_drink, _ = Category.objects.get_or_create(
            name="Food & Drink",
            type_cat=Category.TYPE_EXPENSE,
            slug="food-drink",
        )

        # Create a valid CSV file for testing.
        valid_csv_file_path = os.path.join(os.path.dirname(__file__), "example.csv")
        with open(valid_csv_file_path, "rb") as the_file:
            cls.valid_csv_file = SimpleUploadedFile(
                "example.csv", the_file.read(), content_type="text/csv"
            )

        # Create an invalid CSV file for testing.
        invalid_csv_file_path = os.path.join(
            os.path.dirname(__file__), "example_invalid_date.csv"
        )
        with open(invalid_csv_file_path, "rb") as the_file:
            cls.invalid_csv_file = SimpleUploadedFile(
                "example.csv", the_file.read(), content_type="text/csv"
            )

        # Create a non-CSV file for testing.
        non_csv_file_path = os.path.join(os.path.dirname(__file__), "example.json")
        with open(non_csv_file_path, "rb") as the_file:
            cls.non_csv_file = SimpleUploadedFile(
                "example.json", the_file.read(), content_type="text/json"
            )

    def test_upload_valid_csv(self):
        # Currently, there are no CSVImport objects.
        self.assertEqual(CSVImport.objects.count(), 0)
        # Currently, there are no transactions.
        self.assertEqual(ExpenseTransaction.objects.count(), 0)
        self.assertEqual(EarningTransaction.objects.count(), 0)
        # Currently, there are no Months.
        self.assertEqual(Month.objects.count(), 0)

        response = self.client.post(
            reverse("upload_csv"),
            {"file": self.valid_csv_file},
        )
        self.assertEqual(response.status_code, 302)  # Check for redirect
        self.assertRedirects(response, reverse("transactions"))

        # Check for success message
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(
            str(messages[0]), "CSV file uploaded. 3 transaction(s) created."
        )

        # Check that a CSVImport object was created
        self.assertEqual(CSVImport.objects.count(), 1)
        # Check that 3 Transaction objects were created
        self.assertEqual(ExpenseTransaction.objects.count(), 2)
        self.assertEqual(EarningTransaction.objects.count(), 1)
        # Check that a Month was created.
        self.assertEqual(Month.objects.count(), 1)

    def test_upload_invalid_csv(self):
        response = self.client.post(
            reverse("upload_csv"),
            {"file": self.invalid_csv_file},
        )
        self.assertEqual(
            response.status_code, 200
        )  # Check for rendering the form again

        # Check for error message
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertTrue(str(messages[0]).startswith("Error(s) processing file:"))

        # Check that a CSVImport object was created
        self.assertEqual(CSVImport.objects.count(), 1)
        # Check that no Transaction objects were created
        self.assertEqual(ExpenseTransaction.objects.count(), 0)
        self.assertEqual(EarningTransaction.objects.count(), 0)
        # Check that no Months were created.
        self.assertEqual(Month.objects.count(), 0)

    def test_upload_non_csv_file(self):
        response = self.client.post(
            reverse("upload_csv"),
            {"file": self.non_csv_file},
        )
        self.assertEqual(
            response.status_code, 200
        )  # Check for rendering the form again

        # Check for error message
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertTrue(str(messages[0]).startswith("Error(s) processing file:"))

        # Check that a CSVImport object was created
        self.assertEqual(CSVImport.objects.count(), 1)
        # Check that no Transaction objects were created
        self.assertEqual(ExpenseTransaction.objects.count(), 0)
        self.assertEqual(EarningTransaction.objects.count(), 0)
        # Check that no Months were created.
        self.assertEqual(Month.objects.count(), 0)

    def test_upload_csv_invalid_method(self):
        response = self.client.patch(reverse("upload_csv"))
        self.assertEqual(response.status_code, 405)
