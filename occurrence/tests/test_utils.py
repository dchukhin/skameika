import random
from datetime import date, timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from .. import models, utils
from . import factories


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
        category = factories.CategoryFactory(type_cat=models.Category.TYPE_EARNING)
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
            set(results.values_list("id", flat=True)),
            set([trans1.id, trans2.id, trans3.id]),
        )
        # Each of the transactions now has a running_total_amount field, which
        # is equal to its amount, multiplied by -1
        for transaction in results:
            self.assertEqual(transaction.running_total_amount, transaction.amount * -1)

    def test_not_running_total_category(self):
        """A category that does not have a total_type of TOTAL_TYPE_RUNNING."""
        category = factories.CategoryFactory(total_type=models.Category.TOTAL_TYPE_REGULAR)

        with self.subTest("No transactions"):
            results = utils.get_expensetransactions_running_totals(category)
            self.assertEqual(results.count(), 0)

        with self.subTest("Some transactions"):
            for i in range(0, 3):
                factories.ExpenseTransactionFactory(category=category)
            results = utils.get_expensetransactions_running_totals(category)
            self.assertEqual(results.count(), 3)
            # Since this is not a running type category, the ExpenseTransactions
            # do not have the running_total_amount field
            for transaction in results:
                self.assertFalse(hasattr(transaction, "running_total_amount"))


class GetTransactionsRegularTotalsTestCase(TestCase):
    """Test case for the get_transactions_regular_totals() function."""

    def setUp(self):
        super().setUp()
        self.month = factories.MonthFactory(year=2017, month=9, name="September, 2017")
        self.category_a = factories.CategoryFactory()
        self.category_b = factories.CategoryFactory()
        self.DECIMAL_01 = Decimal(10) ** (-2)

    def assertTotals(self, expected_categories, expected_sum_total, categories, sum_total):
        """Assert Categories and their totals."""
        # The Categories and match the expected Categories
        self.assertEqual(set(expected_categories), set(categories))
        # Each of the Categories has a 'total' field
        for category in categories:
            with self.subTest(category):
                self.assertTrue(hasattr(category, "total"))
        # The expected_sum_total matches the sum_total
        self.assertEqual(expected_sum_total, sum_total)

    def test_no_transactions(self):
        """Get totals when there are no transactions."""
        with self.subTest("No transactions"):
            # Get results
            results, total = utils.get_transactions_regular_totals(self.month)
            # Verify results
            self.assertEqual({}, results)
            self.assertEqual(0, total)

        with self.subTest("Get expense totals with only EarningTransactions"):
            # Create some EarningTransactions
            earning_transs = [factories.EarningTransactionFactory() for i in range(0, 2)]
            # Get results
            results, total = utils.get_transactions_regular_totals(
                self.month,
                type_cat=models.Category.TYPE_EXPENSE,
            )
            # Verify results
            self.assertEqual({}, results)
            self.assertEqual(0, total)

        with self.subTest("Get earning totals with only expense transactions"):
            # Delete any EarningTransactions
            for earning_trans in earning_transs:
                earning_trans.delete()
            # Create some ExpenseTransactions
            for i in range(0, 3):
                factories.ExpenseTransactionFactory()
            # Get results
            results, total = utils.get_transactions_regular_totals(
                self.month,
                type_cat=models.Category.TYPE_EARNING,
            )
            # Verify results
            self.assertEqual({}, results)
            self.assertEqual(0, total)

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

        with self.subTest("No month parameter"):
            # The expected results include both transactions
            expected_results = {
                trans_month.category.id: {
                    "name": trans_month.category.name,
                    "total": trans_month.amount,
                    "children": [],
                },
                trans_different_month.category.id: {
                    "name": trans_different_month.category.name,
                    "total": trans_different_month.amount,
                    "children": [],
                },
            }
            expected_sum_total = sum([trans_month.amount, trans_different_month.amount])
            # Get the results
            results, total = utils.get_transactions_regular_totals()
            # Verify results
            self.assertEqual(expected_results, results)
            self.assertEqual(expected_sum_total, total)

        with self.subTest("With month parameter"):
            # The expected results for the month of trans_month
            expected_results = {
                trans_month.category.id: {
                    "name": trans_month.category.name,
                    "total": trans_month.amount,
                    "children": [],
                },
            }
            expected_sum_total = trans_month.amount
            # Get the results
            results, total = utils.get_transactions_regular_totals(trans_month.month)
            # Verify results
            self.assertEqual(expected_results, results)
            self.assertEqual(expected_sum_total, total)

        with self.subTest("Invalid month parameter"):
            # Passing an invalid month raises an error
            with self.assertRaises(ValueError):
                utils.get_transactions_regular_totals("not a month")

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

        with self.subTest("No type_cat parameter"):
            # The default is to only return expense transactions
            expected_results = {
                trans_expense.category.id: {
                    "name": trans_expense.category.name,
                    "total": Decimal(trans_expense.amount).quantize(self.DECIMAL_01),
                    "children": [],
                },
            }
            expected_sum_total = trans_expense.amount
            # Get the results
            results, total = utils.get_transactions_regular_totals(self.month)
            # Verify results
            self.assertEqual(expected_results, results)
            self.assertEqual(expected_sum_total, total)

        with self.subTest("With type_cat parameter"):
            # Get only the expense transactions

            # Get the results
            results, total = utils.get_transactions_regular_totals(
                self.month, type_cat=trans_expense.category.type_cat
            )
            # Verify results. Expected categories and totals are the same as the
            # previous subtest.
            self.assertEqual(expected_results, results)
            self.assertEqual(expected_sum_total, total)

            # Get only the earning transactions
            expected_results = {
                trans_earning.category.id: {
                    "name": trans_earning.category.name,
                    "total": Decimal(trans_earning.amount).quantize(self.DECIMAL_01),
                    "children": [],
                },
            }
            expected_sum_total = trans_earning.amount
            # Get the results
            results, total = utils.get_transactions_regular_totals(
                self.month, type_cat=trans_earning.category.type_cat
            )
            # Verify results
            self.assertEqual(expected_results, results)
            self.assertEqual(expected_sum_total, total)

        with self.subTest("Invalid type_cat parameter"):
            # Passing an invalid type_cat raises an error
            with self.assertRaises(ValidationError):
                utils.get_transactions_regular_totals(type_cat="not a valid type_cat")

    def test_correct_totals_no_children(self):
        """Verify correct totals for transactions in Categories, with no children."""
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
            date=date(
                year=self.month.year + 1,
                month=self.month.month,
                day=random.randint(1, 28),
            ),
        )
        # A transaction of a different type
        factories.EarningTransactionFactory(
            category=self.category_b,
            amount=40,
            date=date(year=self.month.year, month=self.month.month, day=random.randint(1, 28)),
        )
        # The expected results
        expected_results = {
            self.category_a.id: {
                "name": self.category_a.name,
                "total": Decimal(trans_a1.amount + trans_a2.amount).quantize(self.DECIMAL_01),
                "children": [],
            },
            self.category_b.id: {
                "name": self.category_b.name,
                "total": Decimal(trans_b1.amount).quantize(self.DECIMAL_01),
                "children": [],
            },
        }
        expected_sum_total = sum([trans_a1.amount, trans_a2.amount, trans_b1.amount])
        # Get results
        results, total = utils.get_transactions_regular_totals(self.month)
        # Verify results
        self.assertEqual(expected_results, results)
        self.assertEqual(expected_sum_total, total)

    def test_correct_totals_with_children(self):
        """Verify correct totals for transactions in Categories, with no children."""
        # Create several more Categories, and set their order
        category_a2 = factories.CategoryFactory(order=2)
        category_a3 = factories.CategoryFactory(order=1)
        self.category_a.order = 3
        self.category_a.save()
        # A parent Category for all a Categories
        category_all_a_parent = factories.CategoryFactory()
        for category in [self.category_a, category_a2, category_a3]:
            category.parent = category_all_a_parent
            category.save()

        # ExpenseTransactions in the a Categories
        trans_a = factories.ExpenseTransactionFactory(
            category=self.category_a,
            amount=10,
            date=date(year=self.month.year, month=self.month.month, day=random.randint(1, 28)),
        )
        trans_a2 = factories.ExpenseTransactionFactory(
            category=category_a2,
            amount=20,
            date=date(year=self.month.year, month=self.month.month, day=random.randint(1, 28)),
        )
        trans_a3 = factories.ExpenseTransactionFactory(
            category=category_a3,
            amount=30,
            date=date(year=self.month.year, month=self.month.month, day=random.randint(1, 28)),
        )
        # The parent a Category has a transaction
        trans_aparent = factories.ExpenseTransactionFactory(
            category=category_all_a_parent,
            amount=25,
            date=date(year=self.month.year, month=self.month.month, day=random.randint(1, 28)),
        )

        # A parent Category for all b Categories
        category_all_b_parent = factories.CategoryFactory()
        self.category_b.parent = category_all_b_parent
        self.category_b.save()

        # ExpenseTransactions in the b Categories. The parent b Category does not
        # have any transactions
        trans_b = factories.ExpenseTransactionFactory(
            category=self.category_b,
            amount=80,
            date=date(year=self.month.year, month=self.month.month, day=random.randint(1, 28)),
        )

        # A transaction from a different Month
        factories.ExpenseTransactionFactory(
            category=self.category_b,
            amount=30,
            date=date(
                year=self.month.year + 1,
                month=self.month.month,
                day=random.randint(1, 28),
            ),
        )
        # A transaction of a different type
        factories.EarningTransactionFactory(
            category=self.category_b,
            amount=40,
            date=date(year=self.month.year, month=self.month.month, day=random.randint(1, 28)),
        )

        # The expected results
        category_all_a_parent_total = Decimal(
            sum([trans_aparent.amount, trans_a.amount, trans_a2.amount, trans_a3.amount])
        ).quantize(self.DECIMAL_01)
        category_all_b_parent_total = Decimal(trans_b.amount).quantize(self.DECIMAL_01)
        expected_results = {
            category_all_a_parent.id: {
                "name": category_all_a_parent.name,
                "total": category_all_a_parent_total,
                "children": [
                    {
                        "name": category_a3.name,
                        "total": Decimal(trans_a3.amount).quantize(self.DECIMAL_01),
                    },
                    {
                        "name": category_a2.name,
                        "total": Decimal(trans_a2.amount).quantize(self.DECIMAL_01),
                    },
                    {
                        "name": self.category_a.name,
                        "total": Decimal(trans_a.amount).quantize(self.DECIMAL_01),
                    },
                ],
            },
            category_all_b_parent.id: {
                "name": category_all_b_parent.name,
                "total": category_all_b_parent_total,
                "children": [
                    {
                        "name": self.category_b.name,
                        "total": Decimal(trans_b.amount).quantize(self.DECIMAL_01),
                    },
                ],
            },
        }
        expected_sum_total = sum([category_all_a_parent_total, category_all_b_parent_total])

        # Get results
        results, total = utils.get_transactions_regular_totals(self.month)
        # Verify results
        self.assertEqual(results, expected_results)
        self.assertEqual(expected_sum_total, total)


class GetTransactionsRegularTotalsWithBudgetTestCase(TestCase):
    """Test case for the budget_by_category parameter of get_transactions_regular_totals()."""

    def setUp(self):
        super().setUp()
        self.month = factories.MonthFactory(year=2023, month=6, name="June, 2023")
        self.DECIMAL_01 = Decimal(10) ** (-2)

    def test_no_budget_returns_no_budgeted_keys(self):
        """When budget_by_category is not passed, entries have no 'budgeted' key."""
        category = factories.ExpenseCategoryFactory()
        factories.ExpenseTransactionFactory(
            category=category,
            amount=100,
            date=date(year=2023, month=6, day=15),
        )
        results, _ = utils.get_transactions_regular_totals(self.month)
        for cat_data in results.values():
            self.assertNotIn("budgeted", cat_data)

    def test_empty_budget_returns_no_budgeted_keys(self):
        """When budget_by_category is an empty dict, entries have no 'budgeted' key."""
        category = factories.ExpenseCategoryFactory()
        factories.ExpenseTransactionFactory(
            category=category,
            amount=100,
            date=date(year=2023, month=6, day=15),
        )
        results, _ = utils.get_transactions_regular_totals(
            self.month, budget_by_category={}
        )
        for cat_data in results.values():
            self.assertNotIn("budgeted", cat_data)

    def test_budget_attached_to_category_with_transactions(self):
        """A category with both transactions and a budget gets the correct budgeted value."""
        category = factories.ExpenseCategoryFactory()
        factories.ExpenseTransactionFactory(
            category=category,
            amount=50,
            date=date(year=2023, month=6, day=10),
        )
        budget_amount = Decimal("200.00")
        budget_by_category = {category.id: budget_amount}

        results, total = utils.get_transactions_regular_totals(
            self.month, budget_by_category=budget_by_category
        )

        self.assertIn(category.id, results)
        self.assertEqual(results[category.id]["budgeted"], budget_amount)
        self.assertEqual(
            results[category.id]["total"],
            Decimal("50").quantize(self.DECIMAL_01),
        )

    def test_budget_with_no_transactions_adds_category(self):
        """A category with a budget but no transactions appears with total of 0."""
        category = factories.ExpenseCategoryFactory()
        budget_amount = Decimal("300.00")
        budget_by_category = {category.id: budget_amount}

        results, total = utils.get_transactions_regular_totals(
            self.month, budget_by_category=budget_by_category
        )

        self.assertIn(category.id, results)
        self.assertEqual(results[category.id]["total"], 0)
        self.assertEqual(results[category.id]["budgeted"], budget_amount)
        self.assertEqual(results[category.id]["children"], [])

    def test_budget_only_category_wrong_type_excluded(self):
        """A budget-only category of the wrong type_cat is not included."""
        earning_category = factories.IncomeCategoryFactory()
        budget_by_category = {earning_category.id: Decimal("100.00")}

        results, _ = utils.get_transactions_regular_totals(
            self.month,
            type_cat=models.Category.TYPE_EXPENSE,
            budget_by_category=budget_by_category,
        )

        self.assertNotIn(earning_category.id, results)

    def test_budget_only_category_running_type_excluded(self):
        """A budget-only category with running total_type is not included."""
        category = factories.ExpenseCategoryFactory(
            total_type=models.Category.TOTAL_TYPE_RUNNING
        )
        budget_by_category = {category.id: Decimal("100.00")}

        results, _ = utils.get_transactions_regular_totals(
            self.month, budget_by_category=budget_by_category
        )

        self.assertNotIn(category.id, results)

    def test_category_without_budget_gets_none(self):
        """A category with transactions but no budget entry gets budgeted=None."""
        category = factories.ExpenseCategoryFactory()
        factories.ExpenseTransactionFactory(
            category=category,
            amount=75,
            date=date(year=2023, month=6, day=5),
        )
        # Budget for a different category
        other_category = factories.ExpenseCategoryFactory()
        budget_by_category = {other_category.id: Decimal("50.00")}

        results, _ = utils.get_transactions_regular_totals(
            self.month, budget_by_category=budget_by_category
        )

        self.assertIn(category.id, results)
        self.assertIsNone(results[category.id]["budgeted"])

    def test_budget_on_child_category_with_transactions(self):
        """A child category with both transactions and a budget gets the budgeted value."""
        parent = factories.ExpenseCategoryFactory(order=0)
        child = factories.ExpenseCategoryFactory(parent=parent, order=1)
        factories.ExpenseTransactionFactory(
            category=child,
            amount=40,
            date=date(year=2023, month=6, day=12),
        )
        budget_by_category = {child.id: Decimal("100.00")}

        results, _ = utils.get_transactions_regular_totals(
            self.month, budget_by_category=budget_by_category
        )

        self.assertIn(parent.id, results)
        self.assertEqual(len(results[parent.id]["children"]), 1)
        self.assertEqual(results[parent.id]["children"][0]["budgeted"], Decimal("100.00"))

    def test_budget_on_child_category_no_transactions(self):
        """A child category with a budget but no transactions is added under its parent."""
        parent = factories.ExpenseCategoryFactory(order=0)
        child = factories.ExpenseCategoryFactory(parent=parent, order=1)
        budget_by_category = {child.id: Decimal("150.00")}

        results, _ = utils.get_transactions_regular_totals(
            self.month, budget_by_category=budget_by_category
        )

        self.assertIn(parent.id, results)
        self.assertEqual(results[parent.id]["total"], 0)
        self.assertEqual(len(results[parent.id]["children"]), 1)
        self.assertEqual(results[parent.id]["children"][0]["name"], child.name)
        self.assertEqual(results[parent.id]["children"][0]["total"], 0)
        self.assertEqual(results[parent.id]["children"][0]["budgeted"], Decimal("150.00"))

    def test_budget_on_parent_category(self):
        """A parent category with a budget gets the budgeted value on the parent entry."""
        parent = factories.ExpenseCategoryFactory(order=0)
        child = factories.ExpenseCategoryFactory(parent=parent, order=1)
        factories.ExpenseTransactionFactory(
            category=child,
            amount=60,
            date=date(year=2023, month=6, day=20),
        )
        budget_by_category = {parent.id: Decimal("200.00")}

        results, _ = utils.get_transactions_regular_totals(
            self.month, budget_by_category=budget_by_category
        )

        self.assertIn(parent.id, results)
        self.assertEqual(results[parent.id]["budgeted"], Decimal("200.00"))

    def test_multiple_categories_mixed_budget(self):
        """Multiple categories where some have budgets and some don't."""
        cat_with_budget = factories.ExpenseCategoryFactory()
        cat_without_budget = factories.ExpenseCategoryFactory()
        cat_budget_only = factories.ExpenseCategoryFactory()

        factories.ExpenseTransactionFactory(
            category=cat_with_budget,
            amount=100,
            date=date(year=2023, month=6, day=1),
        )
        factories.ExpenseTransactionFactory(
            category=cat_without_budget,
            amount=200,
            date=date(year=2023, month=6, day=2),
        )

        budget_by_category = {
            cat_with_budget.id: Decimal("150.00"),
            cat_budget_only.id: Decimal("75.00"),
        }

        results, total = utils.get_transactions_regular_totals(
            self.month, budget_by_category=budget_by_category
        )

        # Category with both transaction and budget
        self.assertEqual(results[cat_with_budget.id]["budgeted"], Decimal("150.00"))
        self.assertEqual(
            results[cat_with_budget.id]["total"],
            Decimal("100").quantize(self.DECIMAL_01),
        )

        # Category with transaction but no budget
        self.assertIsNone(results[cat_without_budget.id]["budgeted"])

        # Category with budget but no transaction
        self.assertEqual(results[cat_budget_only.id]["budgeted"], Decimal("75.00"))
        self.assertEqual(results[cat_budget_only.id]["total"], 0)

        # Sum total only includes actual transactions, not budget-only categories
        self.assertEqual(total, Decimal("300").quantize(self.DECIMAL_01))

    def test_earning_type_with_budget(self):
        """Budget works correctly when type_cat is earning."""
        category = factories.IncomeCategoryFactory()
        factories.EarningTransactionFactory(
            category=category,
            amount=500,
            date=date(year=2023, month=6, day=15),
        )
        budget_by_category = {category.id: Decimal("600.00")}

        results, total = utils.get_transactions_regular_totals(
            self.month,
            type_cat=models.Category.TYPE_EARNING,
            budget_by_category=budget_by_category,
        )

        self.assertIn(category.id, results)
        self.assertEqual(results[category.id]["budgeted"], Decimal("600.00"))

    def test_budget_only_child_added_to_existing_parent(self):
        """A budget-only child is appended when its parent already exists from transactions."""
        parent = factories.ExpenseCategoryFactory(order=0)
        child_with_trans = factories.ExpenseCategoryFactory(parent=parent, order=1)
        child_budget_only = factories.ExpenseCategoryFactory(parent=parent, order=2)

        factories.ExpenseTransactionFactory(
            category=child_with_trans,
            amount=80,
            date=date(year=2023, month=6, day=10),
        )
        budget_by_category = {child_budget_only.id: Decimal("120.00")}

        results, _ = utils.get_transactions_regular_totals(
            self.month, budget_by_category=budget_by_category
        )

        self.assertIn(parent.id, results)
        child_names = [c["name"] for c in results[parent.id]["children"]]
        self.assertIn(child_with_trans.name, child_names)
        self.assertIn(child_budget_only.name, child_names)

        # The budget-only child should have total 0 and correct budget
        budget_only_child = next(
            c for c in results[parent.id]["children"] if c["name"] == child_budget_only.name
        )
        self.assertEqual(budget_only_child["total"], 0)
        self.assertEqual(budget_only_child["budgeted"], Decimal("120.00"))


class GetTransactionsRegularTotalsProgressTestCase(TestCase):
    """Test case for the progress_percent calculation in get_transactions_regular_totals()."""

    def setUp(self):
        super().setUp()
        self.month = factories.MonthFactory(year=2023, month=6, name="June, 2023")

    def test_progress_percent_under_budget(self):
        """A category under budget gets the correct progress_percent."""
        category = factories.ExpenseCategoryFactory()
        factories.ExpenseTransactionFactory(
            category=category,
            amount=50,
            date=date(year=2023, month=6, day=15),
        )
        budget_by_category = {category.id: Decimal("100.00")}

        results, _ = utils.get_transactions_regular_totals(
            self.month, budget_by_category=budget_by_category
        )

        self.assertEqual(results[category.id]["progress_percent"], 50)

    def test_progress_percent_at_budget(self):
        """A category exactly at budget gets 100% progress."""
        category = factories.ExpenseCategoryFactory()
        factories.ExpenseTransactionFactory(
            category=category,
            amount=100,
            date=date(year=2023, month=6, day=15),
        )
        budget_by_category = {category.id: Decimal("100.00")}

        results, _ = utils.get_transactions_regular_totals(
            self.month, budget_by_category=budget_by_category
        )

        self.assertEqual(results[category.id]["progress_percent"], 100)

    def test_progress_percent_over_budget(self):
        """A category over budget gets progress_percent greater than 100."""
        category = factories.ExpenseCategoryFactory()
        factories.ExpenseTransactionFactory(
            category=category,
            amount=150,
            date=date(year=2023, month=6, day=15),
        )
        budget_by_category = {category.id: Decimal("100.00")}

        results, _ = utils.get_transactions_regular_totals(
            self.month, budget_by_category=budget_by_category
        )

        self.assertEqual(results[category.id]["progress_percent"], 150)

    def test_progress_percent_no_transactions(self):
        """A budget-only category with no transactions gets 0% progress."""
        category = factories.ExpenseCategoryFactory()
        budget_by_category = {category.id: Decimal("100.00")}

        results, _ = utils.get_transactions_regular_totals(
            self.month, budget_by_category=budget_by_category
        )

        self.assertEqual(results[category.id]["progress_percent"], 0)

    def test_progress_percent_no_budget(self):
        """A category with transactions but no budget gets progress_percent=None."""
        category = factories.ExpenseCategoryFactory()
        factories.ExpenseTransactionFactory(
            category=category,
            amount=50,
            date=date(year=2023, month=6, day=15),
        )
        other_category = factories.ExpenseCategoryFactory()
        budget_by_category = {other_category.id: Decimal("100.00")}

        results, _ = utils.get_transactions_regular_totals(
            self.month, budget_by_category=budget_by_category
        )

        self.assertIsNone(results[category.id]["progress_percent"])

    def test_progress_percent_zero_budget(self):
        """A category with a budget of 0 gets progress_percent=None (avoids division by zero)."""
        category = factories.ExpenseCategoryFactory()
        factories.ExpenseTransactionFactory(
            category=category,
            amount=50,
            date=date(year=2023, month=6, day=15),
        )
        budget_by_category = {category.id: Decimal("0.00")}

        results, _ = utils.get_transactions_regular_totals(
            self.month, budget_by_category=budget_by_category
        )

        self.assertIsNone(results[category.id]["progress_percent"])

    def test_progress_percent_on_child_category(self):
        """A child category gets progress_percent on its child entry."""
        parent = factories.ExpenseCategoryFactory(order=0)
        child = factories.ExpenseCategoryFactory(parent=parent, order=1)
        factories.ExpenseTransactionFactory(
            category=child,
            amount=30,
            date=date(year=2023, month=6, day=12),
        )
        budget_by_category = {child.id: Decimal("100.00")}

        results, _ = utils.get_transactions_regular_totals(
            self.month, budget_by_category=budget_by_category
        )

        child_entry = results[parent.id]["children"][0]
        self.assertEqual(child_entry["progress_percent"], 30)

    def test_no_progress_without_budget_param(self):
        """When budget_by_category is not passed, no progress_percent keys exist."""
        category = factories.ExpenseCategoryFactory()
        factories.ExpenseTransactionFactory(
            category=category,
            amount=50,
            date=date(year=2023, month=6, day=15),
        )

        results, _ = utils.get_transactions_regular_totals(self.month)

        self.assertNotIn("progress_percent", results[category.id])


class GetOrCreateMonthForDateObjTestCase(TestCase):
    """Test case for the get_or_create_month_for_date_obj() function."""

    def test_month_exists(self):
        """If a Month for the date already exists, then it is returned."""
        month = factories.MonthFactory(year=2017, month=9, name="September, 2017")
        date_obj = date(year=month.year, month=month.month, day=1)
        # Get the Month.
        returned_month = utils.get_or_create_month_for_date_obj(date_obj)
        # Assert that the returned_month matches what was expected.
        self.assertEqual(returned_month, returned_month)

    def test_month_does_not_exist(self):
        """If a Month for the date does not exist, then a new Month is created."""
        date_obj = date(year=2018, month=1, day=2)
        # Get the Month.
        returned_month = utils.get_or_create_month_for_date_obj(date_obj)
        # Assert that the returned_month matches what was expected.
        self.assertEqual(returned_month.year, date_obj.year)
        self.assertEqual(returned_month.month, date_obj.month)

    def test_invalid_date_obj(self):
        """Test passing invalid date_obj values."""
        for invalid_value in [
            "2020-01-01",
            "",
            None,
            [],
            {"something": "something else"},
        ]:
            with self.assertRaises(AttributeError):
                utils.get_or_create_month_for_date_obj(invalid_value)


class CreateUniqueSlugTestCase(TestCase):
    """Test case for the create_unique_slug() function."""

    def test_expense_transactions(self):
        """Test the create_unique_slug() function for ExpenseTransactions."""
        category = factories.CategoryFactory(
            type_cat=models.Category.TYPE_EXPENSE,
            total_type=models.Category.TOTAL_TYPE_REGULAR,
        )
        # Create an ExpenseTransaction.
        expense_transaction1 = factories.ExpenseTransactionFactory.build(
            title="Important Transaction",
            category=category,
        )
        # Create a unique slug for the ExpenseTransaction.
        new_slug1 = utils.create_unique_slug_for_transaction(expense_transaction1)
        # Save the ExpenseTransaction.
        expense_transaction1.slug = new_slug1
        expense_transaction1.save()

        # Create another ExpenseTransaction.
        expense_transaction2 = factories.ExpenseTransactionFactory.build(
            title="Important Transaction",
            category=category,
        )
        # Create a unique slug for the ExpenseTransaction.
        new_slug2 = utils.create_unique_slug_for_transaction(expense_transaction2)
        # Save the ExpenseTransaction.
        expense_transaction2.slug = new_slug2
        expense_transaction2.save()

        # Assert that the new_slug1 and new_slug2 are not the same.
        self.assertNotEqual(new_slug1, new_slug2)

    def test_earning_transactions(self):
        """Test the create_unique_slug() function for EarningTransactions."""
        category = factories.CategoryFactory(
            type_cat=models.Category.TYPE_EARNING,
            total_type=models.Category.TOTAL_TYPE_REGULAR,
        )
        # Create an EarningTransaction.
        earning_transaction1 = factories.EarningTransactionFactory.build(
            title="Important Transaction",
            category=category,
        )
        # Create a unique slug for the EarningTransaction.
        new_slug1 = utils.create_unique_slug_for_transaction(earning_transaction1)
        # Save the EarningTransaction.
        earning_transaction1.slug = new_slug1
        earning_transaction1.save()

        # Create another EarningTransaction.
        earning_transaction2 = factories.EarningTransactionFactory.build(
            title="Important Transaction",
            category=category,
        )
        # Create a unique slug for the EarningTransaction.
        new_slug2 = utils.create_unique_slug_for_transaction(earning_transaction2)
        # Save the EarningTransaction.
        earning_transaction2.slug = new_slug2
        earning_transaction2.save()

        # Assert that the new_slug1 and new_slug2 are not the same.
        self.assertNotEqual(new_slug1, new_slug2)

    def test_invalid_inputs(self):
        """Test passing invalid input values."""
        for invalid_value in [
            "not a transaction",
            "",
            None,
            [],
            {"something": "something else"},
        ]:
            with self.assertRaises(AttributeError):
                utils.create_unique_slug_for_transaction(invalid_value)
