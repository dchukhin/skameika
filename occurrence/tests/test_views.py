from datetime import date

from django.test import TestCase
from django.urls import reverse

from . import factories
from .. import models

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
    url_name = 'totals'
    template_name = "occurrence/totals.html"

    def setUp(self):
        super().setUp()
        self.current_month = factories.MonthFactory(
            month=date.today().month,
            year=date.today().year,
            name=date.today().strftime('%B, %Y')
        )
        self.url = reverse(self.url_name)
        self.url_current_month = '{}?month={}'.format(self.url, self.current_month.slug)

    def test_get_no_month(self):
        """GETting the totals view without a month, redirects to totals for current Month."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.url_current_month)

    def test_get_month(self):
        """The view should show all Transactions in the appropriate month."""
        with self.subTest('No Transactions'):
            # A month with no Transactions has no category rows
            response = self.client.get(self.url_current_month)
            self.assertNotContains(response, "category-row")

        with self.subTest('Transactions in 1 Category'):
            category1 = factories.CategoryFactory()
            t1 = factories.ExpenseTransactionFactory(date=date.today(), category=category1)
            t2 = factories.ExpenseTransactionFactory(date=date.today(), category=category1)
            exp_total_category1 = t1.amount + t2.amount
            # A month Transactions in 1 Category has 1 category row
            response = self.client.get(self.url_current_month)
            self.assertContains(response, "name-{}".format(category1.slug))
            self.assertContains(
                response,
                '<td id="total-{}">{}</td>'.format(
                    category1.slug,
                    exp_total_category1
                )
            )

        with self.subTest('Transactions in 1 Category'):
            category2 = factories.CategoryFactory()
            t3 = factories.ExpenseTransactionFactory(date=date.today(), category=category2)
            exp_total_category1 = t1.amount + t2.amount
            exp_total_category2 = t3.amount

            response = self.client.get(self.url_current_month)

            # A month Transactions in multiple Categories has 1 row for each Category
            self.assertContains(response, "name-{}".format(category1.slug))
            self.assertContains(
                response,
                '<td id="total-{}">{}</td>'.format(
                    category1.slug,
                    exp_total_category1
                )
            )
            self.assertContains(response, "name-{}".format(category2.slug))
            self.assertContains(
                response,
                '<td id="total-{}">{}</td>'.format(
                    category2.slug,
                    exp_total_category2
                )
            )


class TestRunningTotalCategoriesTestCase(TestCase):
    url_name = 'running_totals'
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
        with self.subTest('using POST'):
            response = self.client.post(self.url)
            self.assertEqual(response.status_code, 405)

        with self.subTest('using PUT'):
            response = self.client.put(self.url)
            self.assertEqual(response.status_code, 405)

        with self.subTest('using PATCH'):
            response = self.client.patch(self.url)
            self.assertEqual(response.status_code, 405)

        with self.subTest('using DELETE'):
            response = self.client.delete(self.url)
            self.assertEqual(response.status_code, 405)
