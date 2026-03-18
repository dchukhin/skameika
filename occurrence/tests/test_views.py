from datetime import date, datetime
from decimal import Decimal

from django.forms.models import model_to_dict
from django.test import TestCase
from django.urls import reverse
from django.utils.text import slugify

from .. import models
from . import factories
from data_tools.models import CSVImport


# class TestTransactionsView(TestCase):
#     url_name = 'transactions'
#     template_name = "occurrence/transactions.html"
#
#     def test_get_no_month(self):
#         """GETting the transactions view without a month, redirects to current Month."""
#         response = self.client.get(reverse(self.url_name))
#         self.assertEqual(response.status_code, 200)
#         self.assertTemplateUsed(response, self.template_name)
#
#     def test_get_month(self):
#         """The view should show all Transactions in the appropriate month."""


class TestTotalsView(TestCase):
    url_name = "totals"
    template_name = "occurrence/totals.html"

    def setUp(self):
        super().setUp()
        self.current_month = factories.MonthFactory(
            month=date.today().month,
            year=date.today().year,
            name=date.today().strftime("%B, %Y"),
        )
        self.url = reverse(self.url_name)
        self.url_current_month = "{}?month={}".format(self.url, self.current_month.slug)

    def test_get_no_month(self):
        """GETting the totals view without a month, redirects to totals for current Month."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.url_current_month)

    def test_get_month(self):
        """The view should show all Transactions in the appropriate month."""
        with self.subTest("No Transactions"):
            # A month with no Transactions has no category rows
            response = self.client.get(self.url_current_month)
            self.assertNotContains(response, "category-row")

        with self.subTest("Transactions in 1 Category"):
            category1 = factories.CategoryFactory()
            t1 = factories.ExpenseTransactionFactory(
                date=date.today(), category=category1
            )
            t2 = factories.ExpenseTransactionFactory(
                date=date.today(), category=category1
            )
            exp_total_category1 = t1.amount + t2.amount
            # A month Transactions in 1 Category has 1 category row
            response = self.client.get(self.url_current_month)
            self.assertContains(response, "name-{}".format(category1.name))
            self.assertContains(
                response,
                '<td id="total-{}">{}</td>'.format(category1.name, exp_total_category1),
            )

        with self.subTest("Transactions in multiple Categories"):
            category2 = factories.CategoryFactory()
            t3 = factories.ExpenseTransactionFactory(
                date=date.today(), category=category2
            )
            exp_total_category1 = t1.amount + t2.amount
            exp_total_category2 = t3.amount

            response = self.client.get(self.url_current_month)

            # Month Transactions in multiple Categories has 1 row for each Category
            self.assertContains(response, "name-{}".format(category1.name))
            self.assertContains(
                response,
                '<td id="total-{}">{}</td>'.format(category1.name, exp_total_category1),
            )
            self.assertContains(response, "name-{}".format(category2.name))
            self.assertContains(
                response,
                '<td id="total-{}">{}</td>'.format(category2.name, exp_total_category2),
            )

        with self.subTest("Sub Category Transactions"):
            # A parent Category, and a child Category
            category3 = factories.CategoryFactory()
            category3_subcategory = factories.CategoryFactory(parent=category3)
            # A transaction in the child Category
            t4 = factories.ExpenseTransactionFactory(
                date=date.today(), category=category3_subcategory
            )
            # The expected total for both the parent and child Category
            exp_total = t4.amount

            response = self.client.get(self.url_current_month)

            for category in [category3, category3_subcategory]:
                self.assertContains(response, "name-{}".format(category.name))
            self.assertContains(
                response, '<td id="total-{}">{}</td>'.format(category3.name, exp_total)
            )
            self.assertContains(response, '<td id="total-{}">'.format(category3.name))

    def test_statistics(self):
        """GETting the endpoint returns statistics for the month."""
        # A MonthlyStatistic for the current Month
        monthly_statistic_current1 = factories.MonthlyStatisticFactory(
            month=self.current_month
        )
        # A MonthlyStatistic for the wrong Month
        factories.MonthlyStatisticFactory()

        response = self.client.get(self.url_current_month)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            set(response.context["monthly_statistics"]),
            set([monthly_statistic_current1]),
        )

    def test_invalid_methods(self):
        """Only GETting this endpoint is allowed."""
        with self.subTest("using POST"):
            response = self.client.post(self.url)
            self.assertEqual(response.status_code, 405)

        with self.subTest("using PUT"):
            response = self.client.put(self.url)
            self.assertEqual(response.status_code, 405)

        with self.subTest("using PATCH"):
            response = self.client.patch(self.url)
            self.assertEqual(response.status_code, 405)

        with self.subTest("using DELETE"):
            response = self.client.delete(self.url)
            self.assertEqual(response.status_code, 405)


class TestRunningTotalCategoriesTestCase(TestCase):
    url_name = "running_totals"
    template_name = "occurrence/running_totals.html"

    def setUp(self):
        super().setUp()
        self.url = reverse(self.url_name)

    def test_no_running_totals_categories(self):
        """GET the running_totals view when there are no running totals Categories."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_some_running_totals_categories(self):
        """GET the running_totals view when there are some running totals Categories."""
        running_total_cat1 = factories.CategoryFactory(
            total_type=models.Category.TOTAL_TYPE_RUNNING
        )
        running_total_cat2 = factories.CategoryFactory(
            total_type=models.Category.TOTAL_TYPE_RUNNING
        )
        regular_total_cat = factories.CategoryFactory(
            total_type=models.Category.TOTAL_TYPE_REGULAR
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        # Each of the running totals Categories are in the template
        for category in [running_total_cat1, running_total_cat2]:
            with self.subTest(category):
                self.assertContains(response, "name-{}".format(category.slug))
        # The regular total Category is not in the template
        self.assertNotContains(response, "name-{}".format(regular_total_cat.slug))

    def test_invalid_methods(self):
        """Only GETting this endpoint is allowed."""
        with self.subTest("using POST"):
            response = self.client.post(self.url)
            self.assertEqual(response.status_code, 405)

        with self.subTest("using PUT"):
            response = self.client.put(self.url)
            self.assertEqual(response.status_code, 405)

        with self.subTest("using PATCH"):
            response = self.client.patch(self.url)
            self.assertEqual(response.status_code, 405)

        with self.subTest("using DELETE"):
            response = self.client.delete(self.url)
            self.assertEqual(response.status_code, 405)


class TestEditTransactionTestCase(TestCase):
    url_name = "edit_transaction"
    template_name = "occurrence/edit_transaction.html"

    def setUp(self):
        super().setUp()
        self.transaction_expense = factories.ExpenseTransactionFactory()
        self.transaction_earning = factories.EarningTransactionFactory()
        self.url_transaction_expense = reverse(
            self.url_name,
            kwargs={
                "type_cat": models.Category.TYPE_EXPENSE,
                "id": self.transaction_expense.pk,
            },
        )
        self.url_transaction_earning = reverse(
            self.url_name,
            kwargs={
                "type_cat": models.Category.TYPE_EARNING,
                "id": self.transaction_earning.pk,
            },
        )

    def test_get_page(self):
        """GET the page to make an edit to a transaction."""
        with self.subTest("ExpenseTransaction"):
            response = self.client.get(self.url_transaction_expense)
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, self.template_name)
            self.assertEqual(
                response.context["form"].Meta.model, models.ExpenseTransaction
            )

        with self.subTest("EarningTransaction"):
            response = self.client.get(self.url_transaction_earning)
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, self.template_name)
            self.assertEqual(
                response.context["form"].Meta.model, models.EarningTransaction
            )

    def test_post_valid(self):
        """Make a valid POST to update a transaction."""
        new_amount = 50
        new_date = "2017-01-01"
        new_date_month_for_url = slugify("January, 2017")
        new_title = "New Title"
        subtests = (
            (
                "ExpenseTransaction",
                self.transaction_expense,
                self.url_transaction_expense,
            ),
            (
                "EarningTransaction",
                self.transaction_earning,
                self.url_transaction_earning,
            ),
        )
        for subtest_description, transaction, url in subtests:
            with self.subTest(subtest_description):
                data = {
                    "title": new_title,
                    "amount": new_amount,
                    "date": new_date,
                    "category": transaction.category.pk,
                    "description": transaction.description,
                }

                response = self.client.post(url, data=data)

                # The user was redirected to the transactions page for the Month that
                # the transaction is in
                expected_redirect_url = "{}?month={}".format(
                    reverse("transactions"), new_date_month_for_url
                )
                self.assertRedirects(response, expected_redirect_url)
                # The transaction has been updated
                transaction.refresh_from_db()
                self.assertEqual(transaction.title, new_title)
                self.assertEqual(transaction.amount, new_amount)
                self.assertEqual(
                    transaction.date, datetime.strptime(new_date, "%Y-%m-%d").date()
                )

    def test_post_valid_with_next(self):
        """A valid POST with a ?next= param redirects to that URL."""
        next_url = "/some/return/path/"
        for transaction, type_cat in (
            (self.transaction_expense, models.Category.TYPE_EXPENSE),
            (self.transaction_earning, models.Category.TYPE_EARNING),
        ):
            with self.subTest(type_cat=type_cat):
                url = (
                    reverse(self.url_name, kwargs={"type_cat": type_cat, "id": transaction.pk})
                    + f"?next={next_url}"
                )
                data = {
                    "title": "Updated Title",
                    "amount": "50.00",
                    "date": "2022-01-01",
                    "category": transaction.category.pk,
                    "description": transaction.description,
                }
                response = self.client.post(url, data=data)
                self.assertRedirects(response, next_url, fetch_redirect_response=False)

    def test_post_valid_with_unsafe_next(self):
        """A valid POST with an unsafe ?next= param (not starting with /) uses the default redirect."""
        for transaction, type_cat in (
            (self.transaction_expense, models.Category.TYPE_EXPENSE),
            (self.transaction_earning, models.Category.TYPE_EARNING),
        ):
            with self.subTest(type_cat=type_cat):
                url = (
                    reverse(self.url_name, kwargs={"type_cat": type_cat, "id": transaction.pk})
                    + "?next=http://evil.com/"
                )
                data = {
                    "title": "Updated Title",
                    "amount": "50.00",
                    "date": "2022-01-01",
                    "category": transaction.category.pk,
                    "description": transaction.description,
                }
                response = self.client.post(url, data=data)
                expected = "{}?month={}".format(
                    reverse("transactions"), slugify("January, 2022")
                )
                self.assertRedirects(response, expected, fetch_redirect_response=False)

    def test_post_invalid(self):
        """POSTing invalid data to update a transaction."""
        new_amount = 50
        new_date = "invalid date"
        new_title = "New Title"
        subtests = (
            (
                "ExpenseTransaction",
                self.transaction_expense,
                self.url_transaction_expense,
            ),
            (
                "EarningTransaction",
                self.transaction_earning,
                self.url_transaction_earning,
            ),
        )
        for subtest_description, transaction, url in subtests:
            with self.subTest(subtest_description):
                data = {
                    "title": new_title,
                    "amount": new_amount,
                    "date": new_date,
                    "category": transaction.category.pk,
                    "description": transaction.description,
                }

                response = self.client.post(url, data=data, follow=True)

                # The user was not redirected to the transactions page for the
                # Month that the transaction is in, since the data was not valid
                self.assertTemplateUsed(response, self.template_name)
                self.assertFalse(response.context["form"].is_valid())
                # The transaction has not been updated
                transaction.refresh_from_db()
                self.assertNotEqual(transaction.title, new_title)
                self.assertNotEqual(transaction.amount, new_amount)

    def test_invalid_transaction_id(self):
        """GETting and POSTing to the page for an invalid transaction id."""
        invalid_ids = ["a", 1.0, None]

        for invalid_id in invalid_ids:
            invalid_expense_url = self.url_transaction_expense.replace(
                str(self.transaction_expense.pk), str(invalid_id)
            )
            invalid_earning_url = self.url_transaction_earning.replace(
                str(self.transaction_earning.pk), str(invalid_id)
            )

            with self.subTest("GET"):
                response_expense = self.client.get(invalid_expense_url)
                self.assertEqual(response_expense.status_code, 404)

                response_earning = self.client.get(invalid_expense_url)
                self.assertEqual(response_earning.status_code, 404)

            with self.subTest("POST", invalid_id=invalid_id):
                # The data that will be POSTed with each request
                data = {
                    "title": "new title",
                    "amount": 100,
                    "date": "2018-01-01",
                    "description": "new description",
                }

                data["category"] = self.transaction_expense.category.pk
                response_expense = self.client.post(
                    invalid_expense_url, data=data, follow=True
                )
                self.assertEqual(response_expense.status_code, 404)

                data["category"] = self.transaction_earning.category.pk
                response_earning = self.client.post(
                    invalid_earning_url, data=data, follow=True
                )
                self.assertEqual(response_earning.status_code, 404)

    def test_nonexistent_transaction(self):
        """GETting and POSTing to the page for a non-existent transaction."""
        # Urls used in this test
        url_transaction_expense = reverse(
            self.url_name,
            kwargs={
                "type_cat": models.Category.TYPE_EXPENSE,
                "id": self.transaction_expense.pk + 1000000,
            },
        )
        url_transaction_earning = reverse(
            self.url_name,
            kwargs={
                "type_cat": models.Category.TYPE_EARNING,
                "id": self.transaction_earning.pk + 1000000,
            },
        )
        # Data that is POSTed in this test
        data = {
            "title": "new title",
            "amount": 200,
            "date": "2018-01-01",
            "description": "this is the description",
        }

        with self.subTest("GET for non-existent expense transaction"):
            response = self.client.get(url_transaction_expense)
            self.assertEqual(response.status_code, 404)

        with self.subTest("GET for non-existent earning transaction"):
            response = self.client.get(url_transaction_earning)
            self.assertEqual(response.status_code, 404)

        with self.subTest("POST for non-existent expense transaction"):
            data["category"] = self.transaction_expense.category.pk
            response = self.client.post(url_transaction_expense, data=data, follow=True)
            self.assertEqual(response.status_code, 404)

        with self.subTest("POST for non-existent earning transaction"):
            data["category"] = self.transaction_earning.category.pk
            response = self.client.post(url_transaction_earning, data=data, follow=True)
            self.assertEqual(response.status_code, 404)

    def test_invalid_category(self):
        """GETting and POSTing to the page for an invalid category raises 404."""
        invalid_url = reverse(
            self.url_name,
            kwargs={
                "type_cat": "not_a_valid_category",
                "id": self.transaction_expense.pk,
            },
        )
        with self.subTest("GET"):
            response = self.client.get(invalid_url)
            self.assertEqual(response.status_code, 404)

        with self.subTest("POST"):
            data = {
                "title": "new title",
                "amount": 100,
                "date": "2018-01-01",
                "description": "new description",
            }
            response = self.client.post(invalid_url, data=data, follow=True)
            self.assertEqual(response.status_code, 404)

    def test_invalid_methods(self):
        """Only GETting and POSTing to this endpoint is allowed."""
        with self.subTest("using PUT"):
            response = self.client.put(self.url_transaction_expense)
            self.assertEqual(response.status_code, 405)
            response = self.client.put(self.url_transaction_earning)
            self.assertEqual(response.status_code, 405)

        with self.subTest("using PATCH"):
            response = self.client.put(self.url_transaction_expense)
            self.assertEqual(response.status_code, 405)
            response = self.client.put(self.url_transaction_earning)
            self.assertEqual(response.status_code, 405)

        with self.subTest("using DELETE"):
            response = self.client.put(self.url_transaction_expense)
            self.assertEqual(response.status_code, 405)
            response = self.client.put(self.url_transaction_earning)
            self.assertEqual(response.status_code, 405)


class TestCopyTransactionsTestCase(TestCase):
    url_name = "copy_transactions"
    template_name = "occurrence/copy_transactions.html"

    def setUp(self):
        super().setUp()
        self.transaction_expense1 = factories.ExpenseTransactionFactory()
        self.transaction_expense2 = factories.ExpenseTransactionFactory()
        self.transaction_expense3 = factories.ExpenseTransactionFactory()
        self.transaction_earning1 = factories.EarningTransactionFactory()
        self.transaction_earning2 = factories.EarningTransactionFactory()
        self.transaction_earning3 = factories.EarningTransactionFactory()

    def assert_transactions_have_same_data(self, transaction1, transaction2):
        """
        Assert that two transactions have the same data.

        Note: we specifically use model_to_dict(), to make sure that any future field
        additions to the transaction model get checked in this test class.
        """
        data_transaction1 = model_to_dict(transaction1)
        data_transaction2 = model_to_dict(transaction2)

        for field_name, field_value in data_transaction1.items():
            if field_name not in ["id", "slug", "date", "month"]:
                self.assertEqual(
                    data_transaction2[field_name],
                    field_value,
                    f"field '{field_name}' does not match",
                )

    def test_get_page(self):
        """GET the page to copy transactions."""
        with self.subTest("ExpenseTransaction"):
            url = reverse(self.url_name) + (
                f"?transaction_type={models.Category.TYPE_EXPENSE}"
                f"&selected_transactions={self.transaction_expense1.id}"
            )
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, self.template_name)
            self.assertEqual(
                [transaction for transaction in response.context["transactions"]],
                [self.transaction_expense1],
            )

        with self.subTest("EarningTransaction"):
            url = reverse(self.url_name) + (
                f"?transaction_type={models.Category.TYPE_EARNING}"
                f"&selected_transactions={self.transaction_earning1.id}"
            )
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, self.template_name)
            self.assertEqual(
                [transaction for transaction in response.context["transactions"]],
                [self.transaction_earning1],
            )

    def test_get_invalid_params(self):
        """GET the page to copy transactions, but without sending necessary parameters."""
        with self.subTest("no transaction_type"):
            url = reverse(self.url_name) + (
                f"?selected_transactions={self.transaction_expense1.id}"
            )
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, self.template_name)
            expected_error = "You must choose a valid transaction_type (either 'expense' or 'income')."
            self.assertEqual(response.context["errors"], [expected_error])

        with self.subTest("invalid transaction_type"):
            url = reverse(self.url_name) + (
                f"?transaction_type=something"
                f"&selected_transactions={self.transaction_expense1.id}"
            )
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, self.template_name)
            expected_error = "You must choose a valid transaction_type (either 'expense' or 'income')."
            self.assertEqual(response.context["errors"], [expected_error])

        with self.subTest("no selected_transactions"):
            url = reverse(self.url_name) + (
                f"?transaction_type={models.Category.TYPE_EXPENSE}"
            )
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, self.template_name)
            self.assertEqual(response.context["errors"], [])
            self.assertEqual([t for t in response.context["transactions"]], [])

        with self.subTest("invalid selected_transactions"):
            url = reverse(self.url_name) + (
                f"?transaction_type={models.Category.TYPE_EXPENSE}"
                f"&selected_transactions=a"
            )
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, self.template_name)
            self.assertEqual(
                response.context["errors"],
                ["The selected transaction ids must be integers."],
            )

        with self.subTest("non-existent selected_transactions"):
            url = reverse(self.url_name) + (
                f"?transaction_type={models.Category.TYPE_EXPENSE}"
                # an ExpenseTransaction with this id does not exist
                f"&selected_transactions=1000000000000000"
            )
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, self.template_name)
            self.assertEqual(
                response.context["errors"],
                ["One or more of the selected transactions does not exist."],
            )

        with self.subTest("an existent and a non-existent selected_transactions"):
            url = reverse(self.url_name) + (
                f"?transaction_type={models.Category.TYPE_EXPENSE}"
                # an ExpenseTransaction with this id does not exist
                f"&selected_transactions={self.transaction_expense1.id}"
                "&selected_transactions=1000000000000000"
            )
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, self.template_name)
            self.assertEqual(
                response.context["errors"],
                ["One or more of the selected transactions does not exist."],
            )

    def test_post_valid(self):
        """Make a valid POST to copy transactions."""
        # The date string that will be used in this test.
        new_date_str = "2020-01-01"
        # Currently, no transactions exist for the new_date_str.
        self.assertEqual(
            models.ExpenseTransaction.objects.filter(date=new_date_str).count(), 0
        )
        self.assertEqual(
            models.EarningTransaction.objects.filter(date=new_date_str).count(), 0
        )

        data = {"date": new_date_str}

        with self.subTest("ExpenseTransactions"):
            data["transaction_type"] = models.Category.TYPE_EXPENSE
            data["selected_transactions"] = [
                self.transaction_expense1.id,
                self.transaction_expense2.id,
            ]

            response = self.client.post(reverse(self.url_name), data)

            # The user was redirected to the transactions page.
            expected_redirect_url = reverse("transactions")
            self.assertRedirects(response, expected_redirect_url)
            # Two new transactions have been created.
            self.assertEqual(
                models.ExpenseTransaction.objects.filter(date=new_date_str).count(),
                2,
            )
            # There are now 2 transactions with the title that self.transaction_expense1 has.
            self.assertEqual(
                models.ExpenseTransaction.objects.filter(
                    title=self.transaction_expense1.title
                ).count(),
                2,
            )
            # There are now 2 transactions with the title that self.transaction_expense2 has.
            self.assertEqual(
                models.ExpenseTransaction.objects.filter(
                    title=self.transaction_expense2.title
                ).count(),
                2,
            )
            # There is only 1 transaction with the title that self.transaction_expense3 has.
            self.assertEqual(
                models.ExpenseTransaction.objects.filter(
                    title=self.transaction_expense3.title
                ).count(),
                1,
            )

            # Make sure that the new transactions have the same data as the transactions
            # that they copied.
            new_transaction1 = models.ExpenseTransaction.objects.get(
                date=new_date_str, title=self.transaction_expense1.title
            )
            new_transaction2 = models.ExpenseTransaction.objects.get(
                date=new_date_str, title=self.transaction_expense2.title
            )
            self.assert_transactions_have_same_data(
                self.transaction_expense1, new_transaction1
            )
            self.assert_transactions_have_same_data(
                self.transaction_expense2, new_transaction2
            )

        with self.subTest("EarningTransactions"):
            data["transaction_type"] = models.Category.TYPE_EARNING
            data["selected_transactions"] = [self.transaction_earning1.id]

            response = self.client.post(reverse(self.url_name), data)

            # The user was redirected to the transactions page.
            expected_redirect_url = reverse("transactions")
            self.assertRedirects(response, expected_redirect_url)
            # One new transaction has been created.
            self.assertEqual(
                models.EarningTransaction.objects.filter(date=new_date_str).count(), 1
            )
            # There are now 2 transactions with the title that self.transaction_earning1 has.
            self.assertEqual(
                models.EarningTransaction.objects.filter(
                    title=self.transaction_earning1.title
                ).count(),
                2,
            )
            # There is only 1 transaction with the title that self.transaction_earning2 has.
            self.assertEqual(
                models.EarningTransaction.objects.filter(
                    title=self.transaction_earning2.title
                ).count(),
                1,
            )
            # There is only 1 transaction with the title that self.transaction_earning3 has.
            self.assertEqual(
                models.EarningTransaction.objects.filter(
                    title=self.transaction_earning3.title
                ).count(),
                1,
            )
            # Make sure that the new transactions have the same data as the transactions
            # that they copied.
            new_transaction1 = models.EarningTransaction.objects.get(
                date=new_date_str, title=self.transaction_earning1.title
            )
            self.assert_transactions_have_same_data(
                self.transaction_earning1, new_transaction1
            )

    def test_post_invalid(self):
        """Make an invalid POST to copy transactions."""
        # The date string that will be used in this test.
        new_date_str = "2020-01-01"
        # Currently, no transactions exist for the new_date_str.
        self.assertEqual(
            models.ExpenseTransaction.objects.filter(date=new_date_str).count(), 0
        )
        self.assertEqual(
            models.EarningTransaction.objects.filter(date=new_date_str).count(), 0
        )

        data = {"date": new_date_str}

        count_expense_transactions = models.ExpenseTransaction.objects.count()
        count_earning_transactions = models.EarningTransaction.objects.count()

        with self.subTest("no transaction_type"):
            data["selected_transactions"] = [self.transaction_earning1.id]

            response = self.client.post(reverse(self.url_name), data)

            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, self.template_name)
            expected_error = "You must choose a valid transaction_type (either 'expense' or 'income')."
            self.assertEqual(response.context["errors"], [expected_error])
            # No transactions were created.
            self.assertEqual(
                models.ExpenseTransaction.objects.count(), count_expense_transactions
            )
            self.assertEqual(
                models.EarningTransaction.objects.count(), count_earning_transactions
            )

        with self.subTest("invalid transaction_type"):
            data["transaction_type"] = "not a valid transaction_type"
            data["selected_transactions"] = [self.transaction_earning1.id]

            response = self.client.post(reverse(self.url_name), data)
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, self.template_name)
            expected_error = "You must choose a valid transaction_type (either 'expense' or 'income')."
            self.assertEqual(response.context["errors"], [expected_error])
            # No transactions were created.
            self.assertEqual(
                models.ExpenseTransaction.objects.count(), count_expense_transactions
            )
            self.assertEqual(
                models.EarningTransaction.objects.count(), count_expense_transactions
            )

        with self.subTest("no selected_transactions"):
            data["transaction_type"] = models.Category.TYPE_EARNING
            data["selected_transactions"] = []

            response = self.client.post(reverse(self.url_name), data)

            # The user was redirected to the transactions page.
            expected_redirect_url = reverse("transactions")
            self.assertRedirects(response, expected_redirect_url)
            # No transactions were created.
            self.assertEqual(
                models.ExpenseTransaction.objects.count(), count_expense_transactions
            )
            self.assertEqual(
                models.EarningTransaction.objects.count(), count_expense_transactions
            )

        with self.subTest("invalid selected_transactions"):
            data["transaction_type"] = models.Category.TYPE_EARNING
            data["selected_transactions"] = ["not a valid id"]

            response = self.client.post(reverse(self.url_name), data)

            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, self.template_name)
            self.assertEqual(
                response.context["errors"],
                ["The selected transaction ids must be integers."],
            )
            # No transactions were created.
            self.assertEqual(
                models.ExpenseTransaction.objects.count(), count_expense_transactions
            )
            self.assertEqual(
                models.EarningTransaction.objects.count(), count_expense_transactions
            )

        with self.subTest("non-existent selected_transactions"):
            data["transaction_type"] = models.Category.TYPE_EARNING
            data["selected_transactions"] = [1000000000000000]

            response = self.client.post(reverse(self.url_name), data)

            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, self.template_name)
            self.assertEqual(
                response.context["errors"],
                ["One or more of the selected transactions does not exist."],
            )
            # No transactions were created.
            self.assertEqual(
                models.ExpenseTransaction.objects.count(), count_expense_transactions
            )
            self.assertEqual(
                models.EarningTransaction.objects.count(), count_expense_transactions
            )

        with self.subTest("an existent and a non-existent selected_transactions"):
            data["transaction_type"] = models.Category.TYPE_EARNING
            data["selected_transactions"] = [
                self.transaction_expense1.id,
                1000000000000000,
            ]

            response = self.client.post(reverse(self.url_name), data)

            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, self.template_name)
            self.assertEqual(
                response.context["errors"],
                ["One or more of the selected transactions does not exist."],
            )
            # No transactions were created.
            self.assertEqual(
                models.ExpenseTransaction.objects.count(), count_expense_transactions
            )
            self.assertEqual(
                models.EarningTransaction.objects.count(), count_expense_transactions
            )

        with self.subTest("invalid date"):
            data["transaction_type"] = models.Category.TYPE_EARNING
            data["selected_transactions"] = [self.transaction_earning1.id]
            data["date"] = "not a valid date"

            response = self.client.post(reverse(self.url_name), data)

            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, self.template_name)
            expected_error = f"You must choose a date in the appropriate format. '{data['date']}' is not valid."
            self.assertEqual(response.context["errors"], [expected_error])


class TestCSVImportTransactionsView(TestCase):
    url_name = "csv_import_transactions"
    template_name = "occurrence/transactions.html"

    def setUp(self):
        super().setUp()
        # Create a CSV import
        self.csv_import = CSVImport.objects.create(file="test.csv")

        # Create transactions with and without CSV import
        self.expense_transaction_with_import = factories.ExpenseTransactionFactory(
            csv_import=self.csv_import
        )
        self.earning_transaction_with_import = factories.EarningTransactionFactory(
            csv_import=self.csv_import
        )

        # Transactions without CSV import (should not appear in results)
        self.expense_transaction_without_import = factories.ExpenseTransactionFactory(
            csv_import=None
        )
        self.earning_transaction_without_import = factories.EarningTransactionFactory(
            csv_import=None
        )

        self.url = reverse(self.url_name, kwargs={"csv_import_id": self.csv_import.id})

    def test_get_with_valid_csv_import_id(self):
        """GET the view with a valid CSV import ID."""
        url = reverse(self.url_name, kwargs={"csv_import_id": self.csv_import.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)

        # Check context contains the correct CSV import
        self.assertEqual(response.context["csv_import"], self.csv_import)

        # Check that transactions with the CSV import are included
        expense_transactions = list(response.context["expense_transactions"])
        earning_transactions = list(response.context["earning_transactions"])

        self.assertIn(self.expense_transaction_with_import, expense_transactions)
        self.assertIn(self.earning_transaction_with_import, earning_transactions)

        # Check that transactions without the CSV import are not included
        self.assertNotIn(self.expense_transaction_without_import, expense_transactions)
        self.assertNotIn(self.earning_transaction_without_import, earning_transactions)

        # Check context includes category constants
        self.assertEqual(
            response.context["expense_transaction_constant"],
            models.Category.TYPE_EXPENSE,
        )
        self.assertEqual(
            response.context["earning_transaction_constant"],
            models.Category.TYPE_EARNING,
        )

    def test_get_with_invalid_csv_import_id(self):
        """GET the view with an invalid CSV import ID."""
        url = reverse(self.url_name, kwargs={"csv_import_id": 99999})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_get_with_non_numeric_csv_import_id(self):
        """GET the view with a non-numeric CSV import ID."""
        # This test may not be applicable if the URL pattern only accepts [0-9]+
        # But we can test with a string that contains valid characters for [-\w]+
        url = reverse(self.url_name, kwargs={"csv_import_id": "123456789"}).replace(
            "123456789", "invalid"
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_empty_results(self):
        """GET the view for a CSV import with no transactions."""
        empty_csv_import = CSVImport.objects.create(file="empty.csv")
        url = reverse(self.url_name, kwargs={"csv_import_id": empty_csv_import.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        self.assertEqual(response.context["csv_import"], empty_csv_import)
        self.assertEqual(len(response.context["expense_transactions"]), 0)
        self.assertEqual(len(response.context["earning_transactions"]), 0)

    def test_invalid_methods(self):
        """Only GET requests should be allowed."""
        url = reverse(self.url_name, kwargs={"csv_import_id": self.csv_import.id})

        with self.subTest("using POST"):
            response = self.client.post(url)
            self.assertEqual(response.status_code, 405)

        with self.subTest("using PUT"):
            response = self.client.put(url)
            self.assertEqual(response.status_code, 405)

        with self.subTest("using PATCH"):
            response = self.client.patch(url)
            self.assertEqual(response.status_code, 405)

        with self.subTest("using DELETE"):
            response = self.client.delete(url)
            self.assertEqual(response.status_code, 405)


class TestCSVImportListView(TestCase):
    url_name = "csv_import_list"
    template_name = "occurrence/csv_import_list.html"

    def setUp(self):
        super().setUp()
        self.url = reverse(self.url_name)

    def test_get_empty_list(self):
        """GET the view when no CSV imports exist."""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        self.assertEqual(len(response.context["csv_imports"]), 0)

    def test_get_with_csv_imports(self):
        """GET the view with multiple CSV imports."""
        # Create CSV imports with different creation times
        csv_import1 = CSVImport.objects.create(file="import1.csv")
        csv_import2 = CSVImport.objects.create(file="import2.csv")
        csv_import3 = CSVImport.objects.create(file="import3.csv")

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)

        # Check that all CSV imports are in the context
        csv_imports = list(response.context["csv_imports"])
        self.assertEqual(len(csv_imports), 3)

        # Check that they are ordered by creation time (most recent first)
        # Since they were created in sequence, csv_import3 should be first
        self.assertEqual(csv_imports[0], csv_import3)
        self.assertEqual(csv_imports[1], csv_import2)
        self.assertEqual(csv_imports[2], csv_import1)

    def test_csv_imports_ordered_by_created_at_desc(self):
        """CSV imports should be ordered by created_at in descending order."""
        from django.utils import timezone
        from datetime import timedelta

        now = timezone.now()

        # Create CSV imports with specific creation times
        csv_import_oldest = CSVImport.objects.create(file="oldest.csv")
        csv_import_oldest.created_at = now - timedelta(days=2)
        csv_import_oldest.save()

        csv_import_middle = CSVImport.objects.create(file="middle.csv")
        csv_import_middle.created_at = now - timedelta(days=1)
        csv_import_middle.save()

        csv_import_newest = CSVImport.objects.create(file="newest.csv")
        csv_import_newest.created_at = now
        csv_import_newest.save()

        response = self.client.get(self.url)
        csv_imports = list(response.context["csv_imports"])

        # Should be ordered newest first
        self.assertEqual(csv_imports[0], csv_import_newest)
        self.assertEqual(csv_imports[1], csv_import_middle)
        self.assertEqual(csv_imports[2], csv_import_oldest)

    def test_invalid_methods(self):
        """Only GET requests should be allowed."""
        with self.subTest("using POST"):
            response = self.client.post(self.url)
            self.assertEqual(response.status_code, 405)

        with self.subTest("using PUT"):
            response = self.client.put(self.url)
            self.assertEqual(response.status_code, 405)

        with self.subTest("using PATCH"):
            response = self.client.patch(self.url)
            self.assertEqual(response.status_code, 405)

        with self.subTest("using DELETE"):
            response = self.client.delete(self.url)
            self.assertEqual(response.status_code, 405)


class TestStatisticsChartView(TestCase):
    url_name = "statistics_chart_view"
    template_name = "occurrence/statistics.html"

    def setUp(self):
        super().setUp()
        self.url = reverse(self.url_name)
        self.statistic = factories.StatisticFactory()
        self.month_jan = factories.MonthFactory(year=2023, month=1, name="January, 2023")
        self.month_feb = factories.MonthFactory(year=2023, month=2, name="February, 2023")
        self.month_mar = factories.MonthFactory(year=2023, month=3, name="March, 2023")

    def test_get_no_params(self):
        """GET without params renders the form with no chart data."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        self.assertEqual(response.context["chart_data"], [])
        self.assertIsNone(response.context["selected_statistic"])
        self.assertContains(response, "<form")

    def test_get_partial_params(self):
        """GET with only the statistic param (no months) renders no chart."""
        url = "{}?statistic={}".format(self.url, self.statistic.slug)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["chart_data"], [])

    def test_get_with_all_params(self):
        """GET with all params returns 200 and chart_data in context."""
        ms = factories.MonthlyStatisticFactory(
            statistic=self.statistic, month=self.month_feb
        )
        url = "{}?statistic={}&start_month={}&end_month={}".format(
            self.url,
            self.statistic.slug,
            self.month_jan.slug,
            self.month_mar.slug,
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        self.assertIsNotNone(response.context["chart_data"])
        months_in_data = [d["month"] for d in response.context["chart_data"]]
        self.assertIn(str(ms.month), months_in_data)

    def test_get_data_in_range(self):
        """Only MonthlyStatistics within the date range appear in chart_data."""
        ms_in = factories.MonthlyStatisticFactory(
            statistic=self.statistic, month=self.month_feb
        )
        url = "{}?statistic={}&start_month={}&end_month={}".format(
            self.url,
            self.statistic.slug,
            self.month_jan.slug,
            self.month_mar.slug,
        )
        response = self.client.get(url)
        months_in_data = [d["month"] for d in response.context["chart_data"]]
        self.assertIn(str(ms_in.month), months_in_data)

    def test_get_data_outside_range(self):
        """MonthlyStatistics outside the date range are absent from chart_data."""
        month_outside = factories.MonthFactory(year=2022, month=12, name="December, 2022")
        factories.MonthlyStatisticFactory(
            statistic=self.statistic, month=month_outside
        )
        url = "{}?statistic={}&start_month={}&end_month={}".format(
            self.url,
            self.statistic.slug,
            self.month_jan.slug,
            self.month_mar.slug,
        )
        response = self.client.get(url)
        months_in_data = [d["month"] for d in response.context["chart_data"]]
        self.assertNotIn(str(month_outside), months_in_data)

    def test_get_invalid_statistic(self):
        """GET with a non-existent statistic slug returns 404."""
        url = "{}?statistic=does-not-exist&start_month={}&end_month={}".format(
            self.url, self.month_jan.slug, self.month_mar.slug
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_get_invalid_start_month(self):
        """GET with a non-existent start_month slug returns 404."""
        url = "{}?statistic={}&start_month=does-not-exist&end_month={}".format(
            self.url, self.statistic.slug, self.month_mar.slug
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_get_invalid_end_month(self):
        """GET with a non-existent end_month slug returns 404."""
        url = "{}?statistic={}&start_month={}&end_month=does-not-exist".format(
            self.url, self.statistic.slug, self.month_jan.slug
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_invalid_methods(self):
        """Only GET is allowed; other methods return 405."""
        with self.subTest("using POST"):
            response = self.client.post(self.url)
            self.assertEqual(response.status_code, 405)

        with self.subTest("using PUT"):
            response = self.client.put(self.url)
            self.assertEqual(response.status_code, 405)

        with self.subTest("using PATCH"):
            response = self.client.patch(self.url)
            self.assertEqual(response.status_code, 405)

        with self.subTest("using DELETE"):
            response = self.client.delete(self.url)
            self.assertEqual(response.status_code, 405)


class TestBudgetView(TestCase):
    url_name = "budget"
    template_name = "occurrence/budget.html"

    def setUp(self):
        super().setUp()
        self.current_month = factories.MonthFactory(
            month=date.today().month,
            year=date.today().year,
            name=date.today().strftime("%B, %Y"),
        )
        self.url = reverse(self.url_name)
        self.url_current_month = "{}?month={}".format(self.url, self.current_month.slug)

    def test_get_no_month(self):
        """GETting the budget view without a month uses the current month."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        self.assertEqual(response.context["active_month"], self.current_month)

    def test_get_with_month(self):
        """GETting the budget view with a month param shows that month's budget."""
        other_month = factories.MonthFactory(month=1, year=2020, name="January, 2020")
        url = "{}?month={}".format(self.url, other_month.slug)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["active_month"], other_month)

    def test_get_invalid_month(self):
        """GETting with a non-existent month slug returns 404."""
        url = "{}?month=does-not-exist".format(self.url)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_earning_expense_total_sections(self):
        """Budget rows are split into earning and expense sections with correct totals."""
        earning_cat = factories.IncomeCategoryFactory()
        expense_cat = factories.ExpenseCategoryFactory()
        earning_row = factories.ExpectedMonthlyCategoryTotalFactory(
            category=earning_cat, month=self.current_month, amount=Decimal("1000.00")
        )
        expense_row = factories.ExpectedMonthlyCategoryTotalFactory(
            category=expense_cat, month=self.current_month, amount=Decimal("500.00")
        )

        response = self.client.get(self.url_current_month)

        self.assertEqual(response.status_code, 200)
        self.assertIn(earning_row, response.context["earning_rows"])
        self.assertIn(expense_row, response.context["expense_rows"])
        self.assertEqual(response.context["earning_total"], Decimal("1000.00"))
        self.assertEqual(response.context["expense_total"], Decimal("500.00"))
        self.assertEqual(response.context["total"], Decimal("500.00"))

        # Verify row data appears in HTML
        self.assertContains(response, 'id="category-{}"'.format(earning_row.id))
        self.assertContains(response, 'id="category-{}"'.format(expense_row.id))
        self.assertContains(response, 'id="amount-{}"'.format(earning_row.id))
        self.assertContains(response, 'id="amount-{}"'.format(expense_row.id))

    def test_empty_budget(self):
        """A month with no budget rows shows empty tables."""
        response = self.client.get(self.url_current_month)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["earning_rows"]), 0)
        self.assertEqual(len(response.context["expense_rows"]), 0)
        self.assertEqual(response.context["earning_total"], 0)
        self.assertEqual(response.context["expense_total"], 0)
        self.assertEqual(response.context["total"], 0)

    def test_rows_from_other_months_not_shown(self):
        """Budget rows from other months are not included."""
        other_month = factories.MonthFactory(month=1, year=2020, name="January, 2020")
        row_other = factories.ExpectedMonthlyCategoryTotalFactory(month=other_month)
        row_current = factories.ExpectedMonthlyCategoryTotalFactory(month=self.current_month)

        response = self.client.get(self.url_current_month)

        all_rows = list(response.context["earning_rows"]) + list(response.context["expense_rows"])
        self.assertIn(row_current, all_rows)
        self.assertNotIn(row_other, all_rows)

    def test_post_add_expense_row(self):
        """POSTing valid expense data creates a new budget row."""
        category = factories.ExpenseCategoryFactory()
        # Currently, there is no ExpectedMonthlyCategoryTotal for the month and category.
        self.assertEqual(
            models.ExpectedMonthlyCategoryTotal.objects.filter(
                month=self.current_month, category=category
            ).count(),
            0,
        )

        data = {
            "form_type": models.Category.TYPE_EXPENSE,
            "category": category.pk,
            "amount": "250.00",
        }

        response = self.client.post(self.url_current_month, data=data)

        self.assertRedirects(response, self.url_current_month)
        self.assertEqual(
            models.ExpectedMonthlyCategoryTotal.objects.filter(
                month=self.current_month, category=category
            ).count(),
            1,
        )
        row = models.ExpectedMonthlyCategoryTotal.objects.get(
            month=self.current_month, category=category
        )
        self.assertEqual(row.amount, Decimal("250.00"))

    def test_post_add_earning_row(self):
        """POSTing valid earning data creates a new budget row."""
        category = factories.IncomeCategoryFactory()
        data = {
            "form_type": models.Category.TYPE_EARNING,
            "category": category.pk,
            "amount": "500.00",
        }
        # Currently, there are no ExpectedMonthlyCategoryTotals.
        self.assertEqual(
            models.ExpectedMonthlyCategoryTotal.objects.filter().count(),
            0,
        )

        response = self.client.post(self.url_current_month, data=data)

        self.assertRedirects(response, self.url_current_month)
        self.assertEqual(
            models.ExpectedMonthlyCategoryTotal.objects.filter(
                month=self.current_month, category=category
            ).count(),
            1,
        )
        row = models.ExpectedMonthlyCategoryTotal.objects.get(
            month=self.current_month, category=category
        )
        self.assertEqual(row.amount, Decimal("500.00"))

    def test_post_add_duplicate_row(self):
        """POSTing a row for a category that already exists shows form error."""
        category = factories.ExpenseCategoryFactory()
        factories.ExpectedMonthlyCategoryTotalFactory(
            category=category, month=self.current_month, amount=Decimal("100.00")
        )

        data = {
            "form_type": models.Category.TYPE_EXPENSE,
            "category": category.pk,
            "amount": "200.00",
        }
        response = self.client.post(self.url_current_month, data=data)

        # The page re-renders with form errors (not a redirect)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        self.assertTrue(response.context["expense_form"].errors)
        # Still only one row for this category
        self.assertEqual(
            models.ExpectedMonthlyCategoryTotal.objects.filter(
                month=self.current_month, category=category
            ).count(),
            1,
        )

    def test_post_add_row_invalid_data(self):
        """POSTing invalid data does not create a row."""
        data = {
            "form_type": models.Category.TYPE_EXPENSE,
            "category": "",
            "amount": "not a number",
        }
        response = self.client.post(self.url_current_month, data=data)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["expense_form"].errors)
        self.assertEqual(
            models.ExpectedMonthlyCategoryTotal.objects.filter(month=self.current_month).count(),
            0,
        )

    def test_month_navigation(self):
        """The budget page shows month navigation links."""
        other_month = factories.MonthFactory(month=6, year=2020, name="June, 2020")
        response = self.client.get(self.url_current_month)
        self.assertContains(
            response, '?month={}'.format(other_month.slug)
        )


class TestEditBudgetRowView(TestCase):
    url_name = "edit_budget_row"
    template_name = "occurrence/edit_budget_row.html"

    def setUp(self):
        super().setUp()
        self.month = factories.MonthFactory(
            month=date.today().month,
            year=date.today().year,
            name=date.today().strftime("%B, %Y"),
        )
        self.category = factories.ExpenseCategoryFactory()
        self.row = factories.ExpectedMonthlyCategoryTotalFactory(
            category=self.category, month=self.month, amount=Decimal("100.00")
        )
        self.url = reverse(self.url_name, kwargs={"id": self.row.pk})

    def test_get_edit_form(self):
        """GET renders the edit form pre-filled with existing data."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        self.assertEqual(response.context["form"].instance, self.row)

    def test_post_edit_row(self):
        """POST updates the row and redirects to budget page."""
        data = {
            "category": self.category.pk,
            "amount": "200.00",
        }
        self.assertNotEqual(self.row.amount, Decimal("200.00"))

        response = self.client.post(self.url, data=data)

        expected_redirect = "{}?month={}".format(
            reverse("budget"), self.month.slug
        )
        self.assertRedirects(response, expected_redirect)
        self.row.refresh_from_db()
        self.assertEqual(self.row.amount, Decimal("200.00"))

    def test_post_edit_change_category_to_existing(self):
        """Changing category to one that already has a row shows form error."""
        other_category = factories.ExpenseCategoryFactory()
        factories.ExpectedMonthlyCategoryTotalFactory(
            category=other_category, month=self.month, amount=Decimal("50.00")
        )

        data = {
            "category": other_category.pk,
            "amount": "200.00",
        }
        response = self.client.post(self.url, data=data)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)
        # Original row unchanged
        self.row.refresh_from_db()
        self.assertEqual(self.row.category, self.category)

    def test_post_edit_invalid_data(self):
        """POSTing invalid data re-renders the form with errors."""
        data = {
            "category": self.category.pk,
            "amount": "not a number",
        }
        response = self.client.post(self.url, data=data)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)
        self.row.refresh_from_db()
        self.assertEqual(self.row.amount, Decimal("100.00"))

    def test_edit_nonexistent_row(self):
        """GET/POST for a non-existent row returns 404."""
        url = reverse(self.url_name, kwargs={"id": self.row.pk + 100000})

        with self.subTest("GET"):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 404)

        with self.subTest("POST"):
            response = self.client.post(url, data={"category": self.category.pk, "amount": "1"})
            self.assertEqual(response.status_code, 404)

    def test_invalid_methods(self):
        """Only GET and POST are allowed."""
        with self.subTest("using PUT"):
            response = self.client.put(self.url)
            self.assertEqual(response.status_code, 405)

        with self.subTest("using PATCH"):
            response = self.client.patch(self.url)
            self.assertEqual(response.status_code, 405)

        with self.subTest("using DELETE"):
            response = self.client.delete(self.url)
            self.assertEqual(response.status_code, 405)


class TestDeleteBudgetRowView(TestCase):
    url_name = "delete_budget_row"

    def setUp(self):
        super().setUp()
        self.month = factories.MonthFactory(
            month=date.today().month,
            year=date.today().year,
            name=date.today().strftime("%B, %Y"),
        )
        self.row = factories.ExpectedMonthlyCategoryTotalFactory(
            month=self.month, amount=Decimal("100.00")
        )
        self.url = reverse(self.url_name, kwargs={"id": self.row.pk})

    def test_post_delete_row(self):
        """POST deletes the row and redirects to budget page."""
        response = self.client.post(self.url)

        expected_redirect = "{}?month={}".format(
            reverse("budget"), self.month.slug
        )
        self.assertRedirects(response, expected_redirect)
        self.assertFalse(
            models.ExpectedMonthlyCategoryTotal.objects.filter(pk=self.row.pk).exists()
        )

    def test_get_not_allowed(self):
        """GET returns 405."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)

    def test_delete_nonexistent_row(self):
        """POST for a non-existent row returns 404."""
        url = reverse(self.url_name, kwargs={"id": self.row.pk + 100000})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 404)

    def test_invalid_methods(self):
        """Only POST is allowed."""
        with self.subTest("using PUT"):
            response = self.client.put(self.url)
            self.assertEqual(response.status_code, 405)

        with self.subTest("using PATCH"):
            response = self.client.patch(self.url)
            self.assertEqual(response.status_code, 405)

        with self.subTest("using DELETE"):
            response = self.client.delete(self.url)
            self.assertEqual(response.status_code, 405)


class TestCopyBudgetView(TestCase):
    url_name = "copy_budget"

    def setUp(self):
        super().setUp()
        self.source_month = factories.MonthFactory(
            month=1, year=2020, name="January, 2020"
        )
        self.target_month = factories.MonthFactory(
            month=2, year=2020, name="February, 2020"
        )
        self.url = reverse(self.url_name)

    def test_copy_budget_success(self):
        """All rows are copied from source to target month."""
        cat1 = factories.ExpenseCategoryFactory()
        cat2 = factories.IncomeCategoryFactory()
        factories.ExpectedMonthlyCategoryTotalFactory(
            category=cat1, month=self.source_month, amount=Decimal("100.00")
        )
        factories.ExpectedMonthlyCategoryTotalFactory(
            category=cat2, month=self.source_month, amount=Decimal("200.00")
        )
        self.assertEqual(
            models.ExpectedMonthlyCategoryTotal.objects.filter(
                month=self.target_month
            ).count(),
            0
        )

        data = {
            "source_month": self.source_month.slug,
            "target_month": self.target_month.slug,
        }
        response = self.client.post(self.url, data=data)

        expected_redirect = "{}?month={}".format(
            reverse("budget"), self.target_month.slug
        )
        self.assertRedirects(response, expected_redirect)

        target_rows = models.ExpectedMonthlyCategoryTotal.objects.filter(
            month=self.target_month
        )
        self.assertEqual(target_rows.count(), 2)
        self.assertEqual(
            target_rows.get(category=cat1).amount, Decimal("100.00")
        )
        self.assertEqual(
            target_rows.get(category=cat2).amount, Decimal("200.00")
        )

    def test_copy_budget_with_conflicts(self):
        """No rows are copied when conflicts exist, and all conflicts are reported."""
        cat1 = factories.ExpenseCategoryFactory()
        cat2 = factories.ExpenseCategoryFactory()
        # Source has both categories
        factories.ExpectedMonthlyCategoryTotalFactory(
            category=cat1, month=self.source_month, amount=Decimal("100.00")
        )
        factories.ExpectedMonthlyCategoryTotalFactory(
            category=cat2, month=self.source_month, amount=Decimal("200.00")
        )
        # Target already has cat1
        factories.ExpectedMonthlyCategoryTotalFactory(
            category=cat1, month=self.target_month, amount=Decimal("50.00")
        )

        data = {
            "source_month": self.source_month.slug,
            "target_month": self.target_month.slug,
        }
        response = self.client.post(self.url, data=data, follow=True)

        self.assertEqual(response.status_code, 200)
        # The conflict error message is shown
        messages_list = list(response.context["messages"])
        error_messages = [m for m in messages_list if m.level_tag == "error"]
        self.assertEqual(len(error_messages), 1)
        self.assertIn(cat1.name, str(error_messages[0]))

        # No new rows were created (target still has just 1)
        self.assertEqual(
            models.ExpectedMonthlyCategoryTotal.objects.filter(
                month=self.target_month
            ).count(),
            1,
        )

    def test_copy_budget_all_conflicts(self):
        """When all source rows conflict, no rows are copied and all errors shown."""
        cat1 = factories.ExpenseCategoryFactory()
        cat2 = factories.ExpenseCategoryFactory()
        factories.ExpectedMonthlyCategoryTotalFactory(
            category=cat1, month=self.source_month
        )
        factories.ExpectedMonthlyCategoryTotalFactory(
            category=cat2, month=self.source_month
        )
        # Both already exist in target
        factories.ExpectedMonthlyCategoryTotalFactory(
            category=cat1, month=self.target_month
        )
        factories.ExpectedMonthlyCategoryTotalFactory(
            category=cat2, month=self.target_month
        )

        data = {
            "source_month": self.source_month.slug,
            "target_month": self.target_month.slug,
        }
        response = self.client.post(self.url, data=data, follow=True)

        messages_list = list(response.context["messages"])
        error_messages = [m for m in messages_list if m.level_tag == "error"]
        self.assertEqual(len(error_messages), 2)

    def test_copy_from_empty_month(self):
        """Copying from a month with no budget rows shows info message."""
        data = {
            "source_month": self.source_month.slug,
            "target_month": self.target_month.slug,
        }
        response = self.client.post(self.url, data=data, follow=True)

        self.assertEqual(response.status_code, 200)
        messages_list = list(response.context["messages"])
        info_messages = [m for m in messages_list if m.level_tag == "info"]
        self.assertEqual(len(info_messages), 1)

    def test_copy_budget_invalid_source_month(self):
        """POST with non-existent source month returns 404."""
        data = {
            "source_month": "does-not-exist",
            "target_month": self.target_month.slug,
        }
        response = self.client.post(self.url, data=data)
        self.assertEqual(response.status_code, 404)

    def test_copy_budget_invalid_target_month(self):
        """POST with non-existent target month returns 404."""
        data = {
            "source_month": self.source_month.slug,
            "target_month": "does-not-exist",
        }
        response = self.client.post(self.url, data=data)
        self.assertEqual(response.status_code, 404)

    def test_get_not_allowed(self):
        """GET returns 405."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)

    def test_invalid_methods(self):
        """Only POST is allowed."""
        with self.subTest("using PUT"):
            response = self.client.put(self.url)
            self.assertEqual(response.status_code, 405)

        with self.subTest("using PATCH"):
            response = self.client.patch(self.url)
            self.assertEqual(response.status_code, 405)

        with self.subTest("using DELETE"):
            response = self.client.delete(self.url)
            self.assertEqual(response.status_code, 405)


class TestTotalsViewBudgetColumn(TestCase):
    """Tests for the budgeted column on the totals page."""

    url_name = "totals"
    template_name = "occurrence/totals.html"

    def setUp(self):
        super().setUp()
        self.current_month = factories.MonthFactory(
            month=date.today().month,
            year=date.today().year,
            name=date.today().strftime("%B, %Y"),
        )
        self.url = reverse(self.url_name)
        self.url_current_month = "{}?month={}".format(self.url, self.current_month.slug)

    def test_totals_shows_budgeted_column(self):
        """The totals page shows a Budgeted column header."""
        response = self.client.get(self.url_current_month)
        self.assertContains(response, "Budgeted")

    def test_totals_category_with_budget_and_transactions(self):
        """A category with both transactions and a budget shows both values."""
        category = factories.ExpenseCategoryFactory()
        factories.ExpenseTransactionFactory(
            date=date.today(), category=category, amount=Decimal("50.00")
        )
        factories.ExpectedMonthlyCategoryTotalFactory(
            category=category, month=self.current_month, amount=Decimal("100.00")
        )

        response = self.client.get(self.url_current_month)

        self.assertContains(response, 'id="total-{}"'.format(category.name))
        self.assertContains(
            response,
            '<td id="budgeted-{}">100.00</td>'.format(category.name),
        )

    def test_totals_category_with_transactions_no_budget(self):
        """A category with transactions but no budget shows '-' for budgeted."""
        category = factories.ExpenseCategoryFactory()
        factories.ExpenseTransactionFactory(
            date=date.today(), category=category, amount=Decimal("50.00")
        )

        response = self.client.get(self.url_current_month)

        self.assertContains(
            response,
            '<td id="budgeted-{}">-</td>'.format(category.name),
        )

    def test_totals_category_with_budget_no_transactions(self):
        """A category with a budget but no transactions appears with 0 total."""
        category = factories.ExpenseCategoryFactory()
        factories.ExpectedMonthlyCategoryTotalFactory(
            category=category, month=self.current_month, amount=Decimal("100.00")
        )

        response = self.client.get(self.url_current_month)

        self.assertContains(response, 'id="name-{}"'.format(category.name))
        self.assertContains(
            response,
            '<td id="total-{}">0</td>'.format(category.name),
        )
        self.assertContains(
            response,
            '<td id="budgeted-{}">100.00</td>'.format(category.name),
        )

    def test_totals_progress_bar_expense_under_budget(self):
        """An expense category under budget shows a green progress bar."""
        category = factories.ExpenseCategoryFactory()
        factories.ExpenseTransactionFactory(
            date=date.today(), category=category, amount=Decimal("50.00")
        )
        factories.ExpectedMonthlyCategoryTotalFactory(
            category=category, month=self.current_month, amount=Decimal("100.00")
        )

        response = self.client.get(self.url_current_month)

        # 50/100 = 50%
        self.assertContains(response, "progress-bar-success")
        self.assertContains(response, "50%")

    def test_totals_progress_bar_expense_over_budget(self):
        """An expense category over budget shows a red progress bar with actual percentage."""
        category = factories.ExpenseCategoryFactory()
        factories.ExpenseTransactionFactory(
            date=date.today(), category=category, amount=Decimal("150.00")
        )
        factories.ExpectedMonthlyCategoryTotalFactory(
            category=category, month=self.current_month, amount=Decimal("100.00")
        )

        response = self.client.get(self.url_current_month)

        self.assertContains(response, "progress-bar-danger")
        # Shows actual percentage (150%), not capped
        self.assertContains(response, "150%")

    def test_totals_progress_bar_earning_under_budget(self):
        """An earning category under budget shows a red progress bar."""
        category = factories.IncomeCategoryFactory()
        factories.EarningTransactionFactory(
            date=date.today(), category=category, amount=Decimal("30.00")
        )
        factories.ExpectedMonthlyCategoryTotalFactory(
            category=category, month=self.current_month, amount=Decimal("100.00")
        )

        response = self.client.get(self.url_current_month)

        # Earnings: under budget = danger
        self.assertContains(response, "progress-bar-danger")
        self.assertContains(response, "30%")

    def test_totals_progress_bar_earning_at_budget(self):
        """An earning category at budget shows a green progress bar."""
        category = factories.IncomeCategoryFactory()
        factories.EarningTransactionFactory(
            date=date.today(), category=category, amount=Decimal("100.00")
        )
        factories.ExpectedMonthlyCategoryTotalFactory(
            category=category, month=self.current_month, amount=Decimal("100.00")
        )

        response = self.client.get(self.url_current_month)

        self.assertContains(response, "progress-bar-success")
        self.assertContains(response, "100%")

    def test_totals_no_progress_bar_without_budget(self):
        """A category without a budget shows no progress bar."""
        category = factories.ExpenseCategoryFactory()
        factories.ExpenseTransactionFactory(
            date=date.today(), category=category, amount=Decimal("50.00")
        )

        response = self.client.get(self.url_current_month)

        self.assertNotContains(response, "progress-bar-success")
        self.assertNotContains(response, "progress-bar-danger")

    def test_expense_budget_total_in_context(self):
        """expense_budget_total sums all expense category budgets."""
        cat1 = factories.ExpenseCategoryFactory()
        cat2 = factories.ExpenseCategoryFactory()
        factories.ExpenseTransactionFactory(date=date.today(), category=cat1, amount=Decimal("30.00"))
        factories.ExpenseTransactionFactory(date=date.today(), category=cat2, amount=Decimal("20.00"))
        factories.ExpectedMonthlyCategoryTotalFactory(
            category=cat1, month=self.current_month, amount=Decimal("100.00")
        )
        factories.ExpectedMonthlyCategoryTotalFactory(
            category=cat2, month=self.current_month, amount=Decimal("200.00")
        )

        response = self.client.get(self.url_current_month)

        self.assertEqual(response.context["expense_budget_total"], Decimal("300.00"))

    def test_earning_budget_total_in_context(self):
        """earning_budget_total sums all earning category budgets."""
        cat1 = factories.IncomeCategoryFactory()
        cat2 = factories.IncomeCategoryFactory()
        factories.EarningTransactionFactory(date=date.today(), category=cat1, amount=Decimal("50.00"))
        factories.EarningTransactionFactory(date=date.today(), category=cat2, amount=Decimal("75.00"))
        factories.ExpectedMonthlyCategoryTotalFactory(
            category=cat1, month=self.current_month, amount=Decimal("500.00")
        )
        factories.ExpectedMonthlyCategoryTotalFactory(
            category=cat2, month=self.current_month, amount=Decimal("250.00")
        )

        response = self.client.get(self.url_current_month)

        self.assertEqual(response.context["earning_budget_total"], Decimal("750.00"))

    def test_budget_total_none_when_no_budgets(self):
        """Budget totals are None when no categories have budgets."""
        factories.ExpenseTransactionFactory(
            date=date.today(),
            category=factories.ExpenseCategoryFactory(),
            amount=Decimal("50.00"),
        )

        response = self.client.get(self.url_current_month)

        self.assertIsNone(response.context["expense_budget_total"])

    def test_expense_budget_total_shown_in_total_row(self):
        """The expense total row shows the summed budget total."""
        category = factories.ExpenseCategoryFactory()
        factories.ExpenseTransactionFactory(date=date.today(), category=category, amount=Decimal("50.00"))
        factories.ExpectedMonthlyCategoryTotalFactory(
            category=category, month=self.current_month, amount=Decimal("200.00")
        )

        response = self.client.get(self.url_current_month)

        self.assertContains(response, "200")

    def test_earning_budget_total_shown_in_total_row(self):
        """The earning total row shows the summed budget total."""
        category = factories.IncomeCategoryFactory()
        factories.EarningTransactionFactory(date=date.today(), category=category, amount=Decimal("50.00"))
        factories.ExpectedMonthlyCategoryTotalFactory(
            category=category, month=self.current_month, amount=Decimal("300.00")
        )

        response = self.client.get(self.url_current_month)

        self.assertContains(response, "300")

    def test_expense_total_row_shows_dash_when_no_budget(self):
        """The expense total row shows '-' for budget when no budgets are set."""
        category = factories.ExpenseCategoryFactory()
        factories.ExpenseTransactionFactory(date=date.today(), category=category, amount=Decimal("50.00"))

        response = self.client.get(self.url_current_month)

        self.assertContains(response, "<td>-</td>")

    def test_grand_budget_total_in_context(self):
        """budget_total is earning_budget_total minus expense_budget_total."""
        expense_cat = factories.ExpenseCategoryFactory()
        earning_cat = factories.IncomeCategoryFactory()
        factories.ExpenseTransactionFactory(date=date.today(), category=expense_cat, amount=Decimal("50.00"))
        factories.EarningTransactionFactory(date=date.today(), category=earning_cat, amount=Decimal("80.00"))
        factories.ExpectedMonthlyCategoryTotalFactory(
            category=expense_cat, month=self.current_month, amount=Decimal("200.00")
        )
        factories.ExpectedMonthlyCategoryTotalFactory(
            category=earning_cat, month=self.current_month, amount=Decimal("500.00")
        )

        response = self.client.get(self.url_current_month)

        self.assertEqual(response.context["budget_total"], Decimal("300.00"))

    def test_grand_budget_total_none_when_missing_budget(self):
        """budget_total is None when either earnings or expenses have no budget."""
        expense_cat = factories.ExpenseCategoryFactory()
        factories.ExpenseTransactionFactory(date=date.today(), category=expense_cat, amount=Decimal("50.00"))
        factories.ExpectedMonthlyCategoryTotalFactory(
            category=expense_cat, month=self.current_month, amount=Decimal("200.00")
        )
        # No earning budget set

        response = self.client.get(self.url_current_month)

        self.assertIsNone(response.context["budget_total"])
