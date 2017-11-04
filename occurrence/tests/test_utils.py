from datetime import date, timedelta
import random

from django.core.exceptions import ValidationError
from django.test import TestCase

from . import factories
from .. import models, utils


class GetExpensetransactionsRunningTotalsTestCase(TestCase):
    """Test case for the get_expensetransactions_running_totals() function."""

    def setUp(self):
        self.category = factories.CategoryFactory(total_type=models.Category.TOTAL_TYPE_RUNNING)

    def test_no_category(self):
        """Not passing in a Category raises an error."""
        with self.assertRaises(TypeError):
            utils.get_expensetransactions_running_totals()

    def test_no_transactions(self):
        """A Category with no Transactions."""
        results = utils.get_expensetransactions_running_totals(self.category)
        self.assertEqual(results.count(), 0)

    def test_earning_transactions(self):
        """A Category that only has EarningTransactions."""
        category = factories.CategoryFactory(type_cat=models.Category.TYPE_INCOME)
        for i in range(0, 3):
            factories.EarningTransactionFactory(category=category)
        results = utils.get_expensetransactions_running_totals(self.category)
        self.assertEqual(results.count(), 0)

    def test_correct_amount(self):
        """Test that the correct amounts are returned for ExpenseTransactions."""
        trans1 = factories.ExpenseTransactionFactory(category=self.category)
        trans2 = factories.ExpenseTransactionFactory(category=self.category)
        trans3 = factories.ExpenseTransactionFactory(category=self.category)

        results = utils.get_expensetransactions_running_totals(self.category)

        # The transactions in the results are trans1, trans2, and trans3
        self.assertEqual(results.count(), 3)
        self.assertEqual(
            set(results.values_list('id', flat=True)),
            set([trans1.id, trans2.id, trans3.id])
        )
        # Each of the transactions now has a running_total_amount field, which
        # is equal to its amount, multiplied by -1
        for transaction in results:
            self.assertEqual(transaction.running_total_amount, transaction.amount * -1)

    def test_not_running_total_category(self):
        """A category that does not have a total_type of TOTAL_TYPE_RUNNING."""
        category = factories.CategoryFactory(total_type=models.Category.TOTAL_TYPE_REGULAR)

        with self.subTest('No transactions'):
            results = utils.get_expensetransactions_running_totals(category)
            self.assertEqual(results.count(), 0)

        with self.subTest('Some transactions'):
            for i in range(0, 3):
                factories.ExpenseTransactionFactory(category=category)
            results = utils.get_expensetransactions_running_totals(category)
            self.assertEqual(results.count(), 3)
            # Since this is not a running type category, the ExpenseTransactions
            # do not have the running_total_amount field
            for transaction in results:
                self.assertFalse(hasattr(transaction, 'running_total_amount'))


class GetTransactionsRegularTotalsTestCase(TestCase):
    """Test case for the get_transactions_regular_totals() function."""

    def setUp(self):
        super().setUp()
        self.month = factories.MonthFactory(year=2017, month=9, name='September, 2017')
        self.category_a = factories.CategoryFactory()
        self.category_b = factories.CategoryFactory()

    def assertTotals(self, expected_categories, expected_sum_total, categories, sum_total):
        """Assert Categories and their totals."""
        # The Categories and match the expected Categories
        self.assertEqual(set(expected_categories), set(categories))
        # Each of the Categories has a 'total' field
        for category in categories:
            with self.subTest(category):
                self.assertTrue(hasattr(category, 'total'))
        # The expected_sum_total matches the sum_total
        self.assertEqual(expected_sum_total, sum_total)

    def test_no_transactions(self):
        """Get totals when there are no transactions."""
        with self.subTest('No transactions'):
            # The expected results
            expected_categories = []
            expected_sum_total = 0
            # Get results
            categories, total = utils.get_transactions_regular_totals(self.month)
            # Verify results
            self.assertTotals(expected_categories, expected_sum_total, categories, total)

        with self.subTest('Get expense totals with only EarningTransactions'):
            # Create some EarningTransactions
            earning_transs = [factories.EarningTransactionFactory() for i in range(0, 2)]
            # The expected results
            expected_categories = []
            expected_sum_total = 0
            # Get results
            categories, total = utils.get_transactions_regular_totals(
                self.month,
                type_cat=models.Category.TYPE_EXPENSE,
            )
            # Verify results
            self.assertTotals(expected_categories, expected_sum_total, categories, total)

        with self.subTest('Get income totals with only expense transactions'):
            # Delete any EarningTransactions
            for earning_trans in earning_transs:
                earning_trans.delete()
            # Create some ExpenseTransactions
            for i in range(0, 3):
                factories.ExpenseTransactionFactory()
            # The expected results
            expected_categories = []
            expected_sum_total = 0
            # Get results
            categories, total = utils.get_transactions_regular_totals(
                self.month,
                type_cat=models.Category.TYPE_INCOME,
            )
            # Verify results
            self.assertTotals(expected_categories, expected_sum_total, categories, total)

    def test_month_parameter(self):
        """Passing in a month parameter correctly filters by that Month's transactions."""
        # A transaction from the self.month
        trans_month = factories.ExpenseTransactionFactory(
            category=self.category_a,
            amount=100,
            date=date(year=self.month.year, month=self.month.month, day=random.randint(1, 28)),
        )
        # A transaction that occurred 30 days before the trans_month
        trans_different_month = factories.ExpenseTransactionFactory(
            category=self.category_b,
            amount=200,
            date=trans_month.date - timedelta(days=30),
        )

        with self.subTest('No month parameter'):
            # The expected results
            expected_categories = [self.category_a, self.category_b]
            expected_sum_total = sum([trans_month.amount, trans_different_month.amount])
            # The results include both transactions
            categories, total = utils.get_transactions_regular_totals()
            # Verify results
            self.assertTotals(expected_categories, expected_sum_total, categories, total)

        with self.subTest('With month parameter'):
            # The expected results for the month of trans_month
            expected_categories = [self.category_a]
            expected_sum_total = trans_month.amount
            # The results include both transactions
            categories, total = utils.get_transactions_regular_totals(trans_month.month)
            # Verify results
            self.assertTotals(expected_categories, expected_sum_total, categories, total)

        with self.subTest('Invalid month parameter'):
            # Passing an invalid month raises an error
            with self.assertRaises(ValueError):
                utils.get_transactions_regular_totals('not a month')

    def test_type_cat_parameter(self):
        """Passing in a type_cat parameter correctly filters by that cat_type."""
        # An expense transaction from the self.month
        trans_expense = factories.ExpenseTransactionFactory(
            amount=100,
            date=date(year=self.month.year, month=self.month.month, day=random.randint(1, 28)),
        )
        # An earning transaction from the self.month
        trans_earning = factories.EarningTransactionFactory(
            amount=200,
            date=date(year=self.month.year, month=self.month.month, day=random.randint(1, 28)),
        )

        with self.subTest('No type_cat parameter'):
            # The default is to only return expense transactions
            expected_categories = [trans_expense.category]
            expected_sum_total = trans_expense.amount
            # Get the results
            categories, total = utils.get_transactions_regular_totals(self.month)
            # Verify results
            self.assertTotals(expected_categories, expected_sum_total, categories, total)

        with self.subTest('With type_cat parameter'):
            # Get only the expense transactions
            expected_categories = [trans_expense.category]
            expected_sum_total = trans_expense.amount
            # Get the results
            categories, total = utils.get_transactions_regular_totals(
                self.month,
                type_cat=trans_expense.category.type_cat
            )
            # Verify results
            self.assertTotals(expected_categories, expected_sum_total, categories, total)

            # Get only the earning transactions
            expected_categories = [trans_earning.category]
            expected_sum_total = trans_earning.amount
            # Get the results
            categories, total = utils.get_transactions_regular_totals(
                self.month,
                type_cat=trans_earning.category.type_cat
            )
            # Verify results
            self.assertTotals(expected_categories, expected_sum_total, categories, total)

        with self.subTest('Invalid type_cat parameter'):
            # Passing an invalid type_cat raises an error
            with self.assertRaises(ValidationError):
                utils.get_transactions_regular_totals(type_cat='not a valid type_cat')

    def test_correct_totals(self):
        """Verify correct totals for transactions in Categories."""
        trans_a1 = factories.ExpenseTransactionFactory(
            category=self.category_a,
            amount=10,
            date=date(year=self.month.year, month=self.month.month, day=random.randint(1, 28)),
        )
        trans_a2 = factories.ExpenseTransactionFactory(
            category=self.category_a,
            amount=20,
            date=date(year=self.month.year, month=self.month.month, day=random.randint(1, 28)),
        )
        trans_b1 = factories.ExpenseTransactionFactory(
            category=self.category_b,
            amount=10,
            date=date(year=self.month.year, month=self.month.month, day=random.randint(1, 28)),
        )
        # A transaction from a different Month
        factories.ExpenseTransactionFactory(
            category=self.category_b,
            amount=30,
            date=date(year=self.month.year + 1, month=self.month.month, day=random.randint(1, 28)),
        )
        # A transaction of a different type
        factories.EarningTransactionFactory(
            category=self.category_b,
            amount=40,
            date=date(year=self.month.year, month=self.month.month, day=random.randint(1, 28)),
        )
        # The expected results
        expected_categories = [self.category_a, self.category_b]
        expected_sum_total = sum([trans_a1.amount, trans_a2.amount, trans_b1.amount])
        # Get results
        categories, total = utils.get_transactions_regular_totals(self.month)
        # Verify results
        self.assertTotals(expected_categories, expected_sum_total, categories, total)
