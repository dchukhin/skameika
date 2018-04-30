from datetime import date, datetime

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
            self.assertContains(response, "name-{}".format(category1.name))
            self.assertContains(
                response,
                '<td id="total-{}">{}</td>'.format(
                    category1.name,
                    exp_total_category1
                )
            )

        with self.subTest('Transactions in multiple Categories'):
            category2 = factories.CategoryFactory()
            t3 = factories.ExpenseTransactionFactory(date=date.today(), category=category2)
            exp_total_category1 = t1.amount + t2.amount
            exp_total_category2 = t3.amount

            response = self.client.get(self.url_current_month)

            # Month Transactions in multiple Categories has 1 row for each Category
            self.assertContains(response, "name-{}".format(category1.name))
            self.assertContains(
                response,
                '<td id="total-{}">{}</td>'.format(
                    category1.name,
                    exp_total_category1
                )
            )
            self.assertContains(response, "name-{}".format(category2.name))
            self.assertContains(
                response,
                '<td id="total-{}">{}</td>'.format(
                    category2.name,
                    exp_total_category2
                )
            )

        with self.subTest('Sub Category Transactions'):
            # A parent Category, and a child Category
            category3 = factories.CategoryFactory()
            category3_subcategory = factories.CategoryFactory(parent=category3)
            # A transaction in the child Category
            t4 = factories.ExpenseTransactionFactory(
                date=date.today(),
                category=category3_subcategory
            )
            # The expected total for both the parent and child Category
            exp_total = t4.amount

            response = self.client.get(self.url_current_month)

            for category in [category3, category3_subcategory]:
                self.assertContains(response, "name-{}".format(category.name))
            self.assertContains(
                response,
                '<td id="total-{}">{}</td>'.format(
                    category3.name,
                    exp_total
                )
            )
            self.assertContains(response, '<td id="total-{}">'.format(category3.name))

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


class TestEditTransactionTestCase(TestCase):
    url_name = 'edit_transaction'
    template_name = "occurrence/edit_transaction.html"

    def setUp(self):
        super().setUp()
        self.transaction_expense = factories.ExpenseTransactionFactory()
        self.transaction_earning = factories.EarningTransactionFactory()
        self.url_transaction_expense = reverse(
            self.url_name,
            kwargs={'type_cat': models.Category.TYPE_EXPENSE, 'id': self.transaction_expense.pk}
        )
        self.url_transaction_earning = reverse(
            self.url_name,
            kwargs={'type_cat': models.Category.TYPE_INCOME, 'id': self.transaction_earning.pk}
        )

    def test_get_page(self):
        """GET the page to make an edit to a transaction."""
        with self.subTest('ExpenseTransaction'):
            response = self.client.get(self.url_transaction_expense)
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, self.template_name)
            self.assertEqual(response.context['form'].Meta.model, models.ExpenseTransaction)

        with self.subTest('EarningTransaction'):
            response = self.client.get(self.url_transaction_earning)
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, self.template_name)
            self.assertEqual(response.context['form'].Meta.model, models.EarningTransaction)

    def test_post_valid(self):
        """Make a valid POST to update a transaction."""
        new_amount = 50
        new_date = '2017-01-01'
        new_date_month_for_url = 'January,%202017'
        new_title = 'New Title'
        subtests = (
            ('ExpenseTransaction', self.transaction_expense, self.url_transaction_expense),
            ('EarningTransaction', self.transaction_earning, self.url_transaction_earning),
        )
        for subtest_description, transaction, url in subtests:
            with self.subTest(subtest_description):
                data = {
                    'title': new_title,
                    'amount': new_amount,
                    'date': new_date,
                    'category': transaction.category.pk,
                    'description': transaction.description,
                }

                response = self.client.post(url, data=data)

                # The user was redirected to the transactions page for the Month that
                # the transaction is in
                expected_redirect_url = '{}?month={}'.format(
                    reverse('transactions'),
                    new_date_month_for_url
                )
                # import ipdb; ipdb.set_trace()
                self.assertRedirects(response, expected_redirect_url)
                # The transaction has been updated
                transaction.refresh_from_db()
                self.assertEqual(transaction.title, new_title)
                self.assertEqual(transaction.amount, new_amount)
                self.assertEqual(
                    transaction.date,
                    datetime.strptime(new_date, '%Y-%m-%d').date()
                )

    def test_post_invalid(self):
        """POSTing invalid data to update a transaction."""
        new_amount = 50
        new_date = 'invalid date'
        new_title = 'New Title'
        subtests = (
            ('ExpenseTransaction', self.transaction_expense, self.url_transaction_expense),
            ('EarningTransaction', self.transaction_earning, self.url_transaction_earning),
        )
        for subtest_description, transaction, url in subtests:
            with self.subTest(subtest_description):
                data = {
                    'title': new_title,
                    'amount': new_amount,
                    'date': new_date,
                    'category': transaction.category.pk,
                    'description': transaction.description,
                }

                response = self.client.post(url, data=data, follow=True)

                # The user was not redirected to the transactions page for the
                # Month that the transaction is in, since the data was not valid
                self.assertTemplateUsed(response, self.template_name)
                self.assertFalse(response.context['form'].is_valid())
                # The transaction has not been updated
                transaction.refresh_from_db()
                self.assertNotEqual(transaction.title, new_title)
                self.assertNotEqual(transaction.amount, new_amount)

    def test_invalid_transaction_id(self):
        """GETting and POSTing to the page for an invalid transaction id."""
        invalid_ids = ['a', 1.0, None]

        for invalid_id in invalid_ids:
            invalid_expense_url = self.url_transaction_expense.replace(
                str(self.transaction_expense.pk),
                str(invalid_id)
            )
            invalid_earning_url = self.url_transaction_earning.replace(
                str(self.transaction_earning.pk),
                str(invalid_id)
            )

            with self.subTest('GET'):
                response_expense = self.client.get(invalid_expense_url)
                self.assertEqual(response_expense.status_code, 404)

                response_earning = self.client.get(invalid_expense_url)
                self.assertEqual(response_earning.status_code, 404)

            with self.subTest('POST', invalid_id=invalid_id):
                # The data that will be POSTed with each request
                data = {
                    'title': 'new title',
                    'amount': 100,
                    'date': '2018-01-01',
                    'description': 'new description',
                }

                data['category'] = self.transaction_expense.category.pk
                response_expense = self.client.post(invalid_expense_url, data=data, follow=True)
                self.assertEqual(response_expense.status_code, 404)

                data['category'] = self.transaction_earning.category.pk
                response_earning = self.client.post(invalid_earning_url, data=data, follow=True)
                self.assertEqual(response_earning.status_code, 404)

    def test_nonexistent_transaction(self):
        """GETting and POSTing to the page for a non-existent transaction."""
        # Urls used in this test
        url_transaction_expense = reverse(
            self.url_name,
            kwargs={
                'type_cat': models.Category.TYPE_EXPENSE,
                'id': self.transaction_expense.pk + 1000000
            }
        )
        url_transaction_earning = reverse(
            self.url_name,
            kwargs={
                'type_cat': models.Category.TYPE_INCOME,
                'id': self.transaction_earning.pk + 1000000
            }
        )
        # Data that is POSTed in this test
        data = {
            'title': 'new title',
            'amount': 200,
            'date': '2018-01-01',
            'description': 'this is the description',
        }

        with self.subTest('GET for non-existent expense transaction'):
            response = self.client.get(url_transaction_expense)
            self.assertEqual(response.status_code, 404)

        with self.subTest('GET for non-existent earning transaction'):
            response = self.client.get(url_transaction_earning)
            self.assertEqual(response.status_code, 404)

        with self.subTest('POST for non-existent expense transaction'):
            data['category'] = self.transaction_expense.category.pk
            response = self.client.post(url_transaction_expense, data=data, follow=True)
            self.assertEqual(response.status_code, 404)

        with self.subTest('POST for non-existent earning transaction'):
            data['category'] = self.transaction_earning.category.pk
            response = self.client.post(url_transaction_earning, data=data, follow=True)
            self.assertEqual(response.status_code, 404)

    def test_invalid_category(self):
        """GETting and POSTing to the page for an invalid category raises 404."""
        invalid_url = reverse(
            self.url_name,
            kwargs={'type_cat': 'not_a_valid_category', 'id': self.transaction_expense.pk}
        )
        with self.subTest('GET'):
            response = self.client.get(invalid_url)
            self.assertEqual(response.status_code, 404)

        with self.subTest('POST'):
            data = {
                'title': 'new title',
                'amount': 100,
                'date': '2018-01-01',
                'description': 'new description',
            }
            response = self.client.post(invalid_url, data=data, follow=True)
            self.assertEqual(response.status_code, 404)

    def test_invalid_methods(self):
        """Only GETting and POSTing to this endpoint is allowed."""
        with self.subTest('using PUT'):
            response = self.client.put(self.url_transaction_expense)
            self.assertEqual(response.status_code, 405)
            response = self.client.put(self.url_transaction_earning)
            self.assertEqual(response.status_code, 405)

        with self.subTest('using PATCH'):
            response = self.client.put(self.url_transaction_expense)
            self.assertEqual(response.status_code, 405)
            response = self.client.put(self.url_transaction_earning)
            self.assertEqual(response.status_code, 405)

        with self.subTest('using DELETE'):
            response = self.client.put(self.url_transaction_expense)
            self.assertEqual(response.status_code, 405)
            response = self.client.put(self.url_transaction_earning)
            self.assertEqual(response.status_code, 405)
