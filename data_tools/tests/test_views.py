import os

from django.contrib.messages import get_messages
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

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
        invalid_csv_file_path = os.path.join(os.path.dirname(__file__), "example_invalid_date.csv")
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
        self.assertEqual(str(messages[0]), "CSV file uploaded. 3 transaction(s) created.")

        # Check that a CSVImport object was created
        self.assertEqual(CSVImport.objects.count(), 1)
        # Check that 3 Transaction objects were created
        self.assertEqual(ExpenseTransaction.objects.count(), 2)
        self.assertEqual(EarningTransaction.objects.count(), 1)
        # Check that a Month was created (note: the current Month is also created
        # when the user is redirected to the transactions list page).
        self.assertEqual(Month.objects.count(), 2)
        self.assertEqual(Month.objects.filter(slug="july-2025").count(), 1)

    def test_upload_invalid_csv(self):
        response = self.client.post(
            reverse("upload_csv"),
            {"file": self.invalid_csv_file},
        )
        self.assertEqual(response.status_code, 200)  # Check for rendering the form again

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
        self.assertEqual(response.status_code, 200)  # Check for rendering the form again

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

    def test_upload_csv_long_description_succeeds(self):
        """A row whose Description slugifies past 50 characters imports successfully."""
        path = os.path.join(os.path.dirname(__file__), "example_long_description.csv")
        with open(path, "rb") as the_file:
            upload = SimpleUploadedFile("long.csv", the_file.read(), content_type="text/csv")

        response = self.client.post(reverse("upload_csv"), {"file": upload})

        self.assertRedirects(response, reverse("transactions"))
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(str(messages[0]), "CSV file uploaded. 1 transaction(s) created.")
        self.assertEqual(ExpenseTransaction.objects.count(), 1)

    def test_upload_csv_too_long_title_shows_row_and_field(self):
        """The user-facing message names the failing row and field."""
        path = os.path.join(os.path.dirname(__file__), "example_too_long_title.csv")
        with open(path, "rb") as the_file:
            upload = SimpleUploadedFile("long-title.csv", the_file.read(), content_type="text/csv")

        response = self.client.post(reverse("upload_csv"), {"file": upload})

        self.assertEqual(response.status_code, 200)
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        message = str(messages[0])
        self.assertIn("Row 2", message)
        self.assertIn("title", message)
        expected_error_message = (
            "Error(s) processing file: Row 2 ('long description about the "
            "transaction that continues for ma'): title: Ensure this value has "
            "at most 255 characters (it has 300)."
        )
        self.assertEqual(expected_error_message, message)
        self.assertEqual(ExpenseTransaction.objects.count(), 0)

    def test_upload_undecodable_file(self):
        """A file that cannot be decoded as text still gets an error message
        instead of a server error."""
        upload = SimpleUploadedFile(
            "binary.csv",  # .csv name/content-type so only the decode step can fail
            b"\x89PNG\r\n\x1a\n\x00\xff\xfe\xfd",
            content_type="text/csv",
        )

        response = self.client.post(reverse("upload_csv"), {"file": upload})

        self.assertEqual(response.status_code, 200)
        message = str(list(get_messages(response.wsgi_request))[0])
        self.assertTrue(message.startswith("Error(s) processing file:"))
        self.assertIn("invalid start byte", message)
        self.assertEqual(ExpenseTransaction.objects.count(), 0)

    def test_upload_csv_invalid_method(self):
        response = self.client.patch(reverse("upload_csv"))
        self.assertEqual(response.status_code, 405)
