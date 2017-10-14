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
