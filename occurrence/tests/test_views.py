from datetime import date, datetime

from django.forms.models import model_to_dict
from django.test import TestCase
from django.urls import reverse
from django.utils.text import slugify

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

    def test_statistics(self):
        """GETting the endpoint returns statistics for the month."""
        # A MonthlyStatistic for the current Month
        monthly_statistic_current1 = factories.MonthlyStatisticFactory(month=self.current_month)
        # A MonthlyStatistic for the wrong Month
        factories.MonthlyStatisticFactory()

        response = self.client.get(self.url_current_month)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            set(response.context['monthly_statistics']),
            set([monthly_statistic_current1])
        )

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
            kwargs={'type_cat': models.Category.TYPE_EARNING, 'id': self.transaction_earning.pk}
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
        new_date_month_for_url = slugify('January, 2017')
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
                'type_cat': models.Category.TYPE_EARNING,
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


class TestCopyTransactionsTestCase(TestCase):
    url_name = 'copy_transactions'
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
                    f"field '{field_name}' does not match"
                )

    def test_get_page(self):
        """GET the page to copy transactions."""
        with self.subTest('ExpenseTransaction'):
            url = reverse(self.url_name) + (
                f"?transaction_type={models.Category.TYPE_EXPENSE}"
                f"&selected_transactions={self.transaction_expense1.id}"
            )
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, self.template_name)
            self.assertEqual(
                [transaction for transaction in response.context['transactions']],
                [self.transaction_expense1],
            )

        with self.subTest('EarningTransaction'):
            url = reverse(self.url_name) + (
                f"?transaction_type={models.Category.TYPE_EARNING}"
                f"&selected_transactions={self.transaction_earning1.id}"
            )
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, self.template_name)
            self.assertEqual(
                [transaction for transaction in response.context['transactions']],
                [self.transaction_earning1],
            )

    def test_get_invalid_params(self):
        """GET the page to copy transactions, but without sending necessary parameters."""
        with self.subTest('no transaction_type'):
            url = reverse(self.url_name) + (
                f"?selected_transactions={self.transaction_expense1.id}"
            )
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, self.template_name)
            expected_error = (
                "You must choose a valid transaction_type (either 'expense' or 'income')."
            )
            self.assertEqual(response.context['errors'], [expected_error])

        with self.subTest('invalid transaction_type'):
            url = reverse(self.url_name) + (
                f"?transaction_type=something"
                f"&selected_transactions={self.transaction_expense1.id}"
            )
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, self.template_name)
            expected_error = (
                "You must choose a valid transaction_type (either 'expense' or 'income')."
            )
            self.assertEqual(response.context['errors'], [expected_error])

        with self.subTest('no selected_transactions'):
            url = reverse(self.url_name) + (
                f"?transaction_type={models.Category.TYPE_EXPENSE}"
            )
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, self.template_name)
            self.assertEqual(response.context['errors'], [])
            self.assertEqual([t for t in response.context['transactions']], [])

        with self.subTest('invalid selected_transactions'):
            url = reverse(self.url_name) + (
                f"?transaction_type={models.Category.TYPE_EXPENSE}"
                f"&selected_transactions=a"
            )
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, self.template_name)
            self.assertEqual(response.context['errors'], ['The selected transaction ids must be integers.'])

        with self.subTest('non-existent selected_transactions'):
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
                ["One or more of the selected transactions does not exist."]
            )

        with self.subTest('an existent and a non-existent selected_transactions'):
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
                ["One or more of the selected transactions does not exist."]
            )

    def test_post_valid(self):
        """Make a valid POST to copy transactions."""
        # The date string that will be used in this test.
        new_date_str = '2020-01-01'
        # Currently, no transactions exist for the new_date_str.
        self.assertEqual(models.ExpenseTransaction.objects.filter(date=new_date_str).count(), 0)
        self.assertEqual(models.EarningTransaction.objects.filter(date=new_date_str).count(), 0)

        data = {'date': new_date_str}

        with self.subTest('ExpenseTransactions'):
            data["transaction_type"] = models.Category.TYPE_EXPENSE
            data["selected_transactions"] = [self.transaction_expense1.id, self.transaction_expense2.id]

            response = self.client.post(reverse(self.url_name), data)

            # The user was redirected to the transactions page.
            expected_redirect_url = reverse('transactions')
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
                date=new_date_str,
                title=self.transaction_expense1.title
            )
            new_transaction2 = models.ExpenseTransaction.objects.get(
                date=new_date_str,
                title=self.transaction_expense2.title
            )
            self.assert_transactions_have_same_data(self.transaction_expense1, new_transaction1)
            self.assert_transactions_have_same_data(self.transaction_expense2, new_transaction2)

        with self.subTest('EarningTransactions'):
            data["transaction_type"] = models.Category.TYPE_EARNING
            data["selected_transactions"] = [self.transaction_earning1.id]

            response = self.client.post(reverse(self.url_name), data)

            # The user was redirected to the transactions page.
            expected_redirect_url = reverse('transactions')
            self.assertRedirects(response, expected_redirect_url)
            # One new transaction has been created.
            self.assertEqual(
                models.EarningTransaction.objects.filter(date=new_date_str).count(),
                1
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
                date=new_date_str,
                title=self.transaction_earning1.title
            )
            self.assert_transactions_have_same_data(self.transaction_earning1, new_transaction1)

    def test_post_invalid(self):
        """Make an invalid POST to copy transactions."""
        # The date string that will be used in this test.
        new_date_str = '2020-01-01'
        # Currently, no transactions exist for the new_date_str.
        self.assertEqual(models.ExpenseTransaction.objects.filter(date=new_date_str).count(), 0)
        self.assertEqual(models.EarningTransaction.objects.filter(date=new_date_str).count(), 0)

        data = {'date': new_date_str}

        count_expense_transactions = models.ExpenseTransaction.objects.count()
        count_earning_transactions = models.EarningTransaction.objects.count()

        with self.subTest('no transaction_type'):
            data["selected_transactions"] = [self.transaction_earning1.id]

            response = self.client.post(reverse(self.url_name), data)

            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, self.template_name)
            expected_error = (
                "You must choose a valid transaction_type (either 'expense' or 'income')."
            )
            self.assertEqual(response.context['errors'], [expected_error])
            # No transactions were created.
            self.assertEqual(models.ExpenseTransaction.objects.count(), count_expense_transactions)
            self.assertEqual(models.EarningTransaction.objects.count(), count_expense_transactions)

        with self.subTest('invalid transaction_type'):
            data["transaction_type"] = "not a valid transaction_type"
            data["selected_transactions"] = [self.transaction_earning1.id]

            response = self.client.post(reverse(self.url_name), data)
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, self.template_name)
            expected_error = (
                "You must choose a valid transaction_type (either 'expense' or 'income')."
            )
            self.assertEqual(response.context['errors'], [expected_error])
            # No transactions were created.
            self.assertEqual(models.ExpenseTransaction.objects.count(), count_expense_transactions)
            self.assertEqual(models.EarningTransaction.objects.count(), count_expense_transactions)

        with self.subTest('no selected_transactions'):
            data["transaction_type"] = models.Category.TYPE_EARNING
            data["selected_transactions"] = []

            response = self.client.post(reverse(self.url_name), data)

            # The user was redirected to the transactions page.
            expected_redirect_url = reverse('transactions')
            self.assertRedirects(response, expected_redirect_url)
            # No transactions were created.
            self.assertEqual(models.ExpenseTransaction.objects.count(), count_expense_transactions)
            self.assertEqual(models.EarningTransaction.objects.count(), count_expense_transactions)

        with self.subTest('invalid selected_transactions'):
            data["transaction_type"] = models.Category.TYPE_EARNING
            data["selected_transactions"] = ["not a valid id"]

            response = self.client.post(reverse(self.url_name), data)

            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, self.template_name)
            self.assertEqual(response.context['errors'], ['The selected transaction ids must be integers.'])
            # No transactions were created.
            self.assertEqual(models.ExpenseTransaction.objects.count(), count_expense_transactions)
            self.assertEqual(models.EarningTransaction.objects.count(), count_expense_transactions)

        with self.subTest('non-existent selected_transactions'):
            data["transaction_type"] = models.Category.TYPE_EARNING
            data["selected_transactions"] = [1000000000000000]

            response = self.client.post(reverse(self.url_name), data)

            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, self.template_name)
            self.assertEqual(
                response.context['errors'],
                ["One or more of the selected transactions does not exist."],
            )
            # No transactions were created.
            self.assertEqual(models.ExpenseTransaction.objects.count(), count_expense_transactions)
            self.assertEqual(models.EarningTransaction.objects.count(), count_expense_transactions)

        with self.subTest('an existent and a non-existent selected_transactions'):
            data["transaction_type"] = models.Category.TYPE_EARNING
            data["selected_transactions"] = [self.transaction_expense1.id, 1000000000000000]

            response = self.client.post(reverse(self.url_name), data)

            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, self.template_name)
            self.assertEqual(
                response.context['errors'],
                ["One or more of the selected transactions does not exist."],
            )
            # No transactions were created.
            self.assertEqual(models.ExpenseTransaction.objects.count(), count_expense_transactions)
            self.assertEqual(models.EarningTransaction.objects.count(), count_expense_transactions)

        with self.subTest('invalid date'):
            data["transaction_type"] = models.Category.TYPE_EARNING
            data["selected_transactions"] = [self.transaction_earning1.id]
            data["date"] = "not a valid date"

            response = self.client.post(reverse(self.url_name), data)

            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, self.template_name)
            expected_error = (
                f"You must choose a date in the appropriate format. '{data['date']}' is not valid."
            )
            self.assertEqual(response.context['errors'], [expected_error])
