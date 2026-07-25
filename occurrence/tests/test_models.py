from datetime import date

from django.db.utils import IntegrityError
from django.test import TestCase

from .. import models
from . import factories


class TestCategory(TestCase):
    def test_str(self):
        """Smoke test for string representation."""
        category = factories.CategoryFactory()
        self.assertEqual(str(category), category.name)

    def test_default_type_cat(self):
        """By default, a Category is an expense Category."""
        category = factories.CategoryFactory()
        self.assertEqual(category.type_cat, models.Category.TYPE_EXPENSE)

    def test_default_total_type(self):
        """By default a Cateogry has a total_type of TOTAL_TYPE_REGULAR."""
        category = factories.CategoryFactory()
        self.assertEqual(category.total_type, models.Category.TOTAL_TYPE_REGULAR)

    def test_default_ordering(self):
        """Default ordering is by order field, then by name field."""
        cat_order_1_name_a2 = factories.CategoryFactory(order=1, name="a2")
        cat_order_2_name_a1 = factories.CategoryFactory(order=2, name="a1")
        cat_order_1_name_b2 = factories.CategoryFactory(order=1, name="b2")
        cat_order_2_name_b1 = factories.CategoryFactory(order=2, name="b1")

        with self.subTest("Categories with same order are ordered by name"):
            qs = models.Category.objects.filter(
                id__in=[cat_order_1_name_b2.id, cat_order_1_name_a2.id]
            )
            self.assertEqual(
                set(qs.values_list("id", flat=True)),
                set([cat_order_1_name_a2.id, cat_order_1_name_b2.id]),
            )

        with self.subTest("all Categories"):
            self.assertEqual(
                set(models.Category.objects.all().values_list("id", flat=True)),
                set(
                    [
                        cat_order_1_name_a2.id,
                        cat_order_1_name_b2.id,
                        cat_order_2_name_a1.id,
                        cat_order_2_name_b1.id,
                    ]
                ),
            )

    def test_parent_child_deletion(self):
        """Deleting a parent or child Category does not CASCADE delete the parent or children."""
        parent = factories.CategoryFactory()
        child = factories.CategoryFactory(parent=parent)
        grandchild = factories.CategoryFactory(parent=child)

        # Delete the child, which should not delete either the parent or the
        # grandchild
        child.delete()

        for category in [parent, grandchild]:
            category.refresh_from_db()
            self.assertIsNotNone(
                category.id,
            )


class TestMonth(TestCase):
    def test_str(self):
        """Smoke test for string representation."""
        month = factories.MonthFactory()
        self.assertEqual(str(month), month.name)

    def test_unique_year_month(self):
        """A Month's year and month are unique together."""
        factories.MonthFactory(year=2020, month=1)
        with self.assertRaises(IntegrityError):
            factories.MonthFactory(year=2020, month=1)


class GetOrCreateMonthForDateObjTestCase(TestCase):
    """Test case for the get_or_create_month_for_date_obj() function."""

    def test_month_exists(self):
        """If a Month for the date already exists, then it is returned."""
        month = factories.MonthFactory(year=2017, month=9, name="September, 2017")
        date_obj = date(year=month.year, month=month.month, day=1)

        returned_month = models.get_or_create_month_for_date_obj(date_obj)

        self.assertEqual(returned_month, month)
        self.assertEqual(models.Month.objects.count(), 1)

    def test_month_does_not_exist(self):
        """If a Month for the date does not exist, then a new Month is created."""
        date_obj = date(year=2018, month=1, day=2)

        returned_month = models.get_or_create_month_for_date_obj(date_obj)

        self.assertEqual(returned_month.year, date_obj.year)
        self.assertEqual(returned_month.month, date_obj.month)
        self.assertEqual(returned_month.name, "January, 2018")
        self.assertEqual(returned_month.slug, "january-2018")
        self.assertEqual(models.Month.objects.count(), 1)

    def test_repeated_calls_do_not_create_duplicates(self):
        """Calling this more than once for the same date reuses the same Month."""
        date_obj = date(year=2019, month=3, day=1)

        first_month = models.get_or_create_month_for_date_obj(date_obj)
        second_month = models.get_or_create_month_for_date_obj(date_obj)

        self.assertEqual(first_month, second_month)
        self.assertEqual(models.Month.objects.count(), 1)

    def test_different_days_in_same_month_reuse_the_month(self):
        """Two dates in the same month and year resolve to the same Month."""
        first_month = models.get_or_create_month_for_date_obj(date(year=2019, month=3, day=1))
        second_month = models.get_or_create_month_for_date_obj(date(year=2019, month=3, day=28))

        self.assertEqual(first_month, second_month)
        self.assertEqual(models.Month.objects.count(), 1)

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
                models.get_or_create_month_for_date_obj(invalid_value)

    def test_never_returns_blank_slug(self):
        """The returned Month always has a non-blank slug, whether newly created or reused."""
        date_obj = date(year=2019, month=3, day=10)
        month = models.get_or_create_month_for_date_obj(date_obj)
        self.assertNotEqual(month.slug, "")


class TransactionBaseMixin(object):
    """
    Mixin for Transaction-like models inheriting from TransactionBase.

    To use this mixin, define:
     - self.model_class
     - self.factory
    """

    def test_str(self):
        """Smoke test for string representation."""
        transaction = self.factory()
        self.assertEqual(
            str(transaction),
            "{} - {}".format(transaction.title, transaction.date.strftime("%Y-%m-%d")),
        )

    def test_save_unique_slug(self):
        """Saving a Transaction gives it a unique slug."""
        with self.subTest("First Transaction"):
            # Currently, there are no Transactions
            self.assertEqual(self.model_class.objects.count(), 0)
            transaction1 = self.factory()
            # Now there is 1 Transaction
            self.assertEqual(self.model_class.objects.count(), 1)

        with self.subTest("Second Transaction with same slug"):
            transaction2 = self.factory(slug=transaction1.slug)
            # Now there are 2 Transactions, and their slugs are unique
            self.assertEqual(self.model_class.objects.count(), 2)
            self.assertNotEqual(transaction2.slug, transaction1.slug)

        with self.subTest("Third Transaction with same slug"):
            transaction3 = self.factory(slug=transaction1.slug)
            # Now there are 3 Transactions, and their slugs are unique
            self.assertEqual(self.model_class.objects.count(), 3)
            self.assertNotEqual(transaction3.slug, transaction1.slug)

    def test_save_slug_already_unique(self):
        """Saving a Transaction with a slug that is already unique keeps its slug."""
        test_date = date(year=2017, month=5, day=1)
        unique_slug = "transaction-1-2017-05-01"
        # A transaction with a unique slug
        transaction1 = self.factory(slug=unique_slug, title="Transaction 1", date=test_date)
        # A second transaction with the same title and date as transaction1
        self.factory(title=transaction1.title, date=transaction1.date, slug=unique_slug)

        # Now saving transaction1 should keep its slug, rather than changing it
        # to something new
        transaction1.save()
        self.assertEqual(transaction1.slug, unique_slug)

        # A third transaction with the same title and date as transaction1.
        # Creating it does not cause an error.
        self.factory(title=transaction1.title, date=transaction1.date, slug=unique_slug)

        self.assertEqual(
            set(transaction1.__class__.objects.values_list("slug", flat=True)),
            set(
                [
                    "transaction-1-2017-05-01",
                    "transaction-1-2017-05-01_2",
                    "transaction-1-2017-05-01_3",
                ]
            ),
        )

    def test_save_associate_month(self):
        """Saving a Transaction without a Month associates it with correct Month."""
        with self.subTest("new Transaction with no associated month; no Month object"):
            test_date = date(year=2017, month=5, day=1)
            transaction1 = self.factory(date=test_date, month=None)
            # The transaction1 now has the correct month
            self.assertEqual(transaction1.month.name, test_date.strftime("%B, %Y"))
            may_2017_month = transaction1.month

        with self.subTest("new Transaction with no associated month; Month object exists"):
            # Now the Month for the test_date exists (may_2017_month). The next
            # Transaction in May, 2017 should be associated with it
            transaction2 = self.factory(date=test_date, month=None)
            # The transaction2 now has the correct month
            self.assertEqual(transaction2.month, may_2017_month)

        with self.subTest("new Transaction with associated month"):
            transaction3 = self.factory(date=test_date, month=may_2017_month)
            # The transaction3 is still associated with may_2017_month
            self.assertEqual(transaction3.month, may_2017_month)

        with self.subTest("Transaction associated with wrong Month"):
            june_2017_month = factories.MonthFactory(month=6, year=2017, name="June, 2017")
            transaction3.month = june_2017_month
            transaction3.save()
            # The transaction3 is now associated with may_2017_month
            self.assertEqual(transaction3.month, may_2017_month)

        with self.subTest("changing Transaction date associates it with correct Month"):
            # Currently, transaction3 is associated with may_2017_month
            self.assertEqual(transaction3.month, may_2017_month)
            # Change the transaction3 date to be in June, 2017
            transaction3.date = date(year=2017, month=6, day=15)
            transaction3.save()
            # Now, transaction3 is associated with june_2017_month
            self.assertEqual(transaction3.month, june_2017_month)

    def test_save_creates_month_with_slug_no_duplicate(self):
        """
        Saving a Transaction in a month with no existing Month creates exactly
        one, correctly slugged Month; a second Transaction in the same month
        reuses it rather than creating a duplicate.
        """
        test_date = date(year=2022, month=3, day=10)
        self.assertEqual(models.Month.objects.filter(year=2022, month=3).count(), 0)

        transaction1 = self.factory(date=test_date, month=None)

        months = models.Month.objects.filter(year=2022, month=3)
        self.assertEqual(months.count(), 1)
        self.assertEqual(transaction1.month, months.get())
        self.assertNotEqual(transaction1.month.slug, "")

        transaction2 = self.factory(date=test_date, month=None)
        self.assertEqual(models.Month.objects.filter(year=2022, month=3).count(), 1)
        self.assertEqual(transaction2.month, transaction1.month)


class TestExpenseTransaction(TestCase, TransactionBaseMixin):
    model_class = models.ExpenseTransaction
    factory = factories.ExpenseTransactionFactory


class TestEarningTransaction(TestCase, TransactionBaseMixin):
    model_class = models.EarningTransaction
    factory = factories.EarningTransactionFactory


class TestStatistic(TestCase):
    def test_str(self):
        """Smoke test for string representation."""
        statistic = factories.StatisticFactory()
        self.assertEqual(str(statistic), statistic.name)


class TestMonthlyStatistic(TestCase):
    def test_str(self):
        """Smoke test for string representation."""
        monthly_statistic = factories.MonthlyStatisticFactory()
        self.assertEqual(
            str(monthly_statistic),
            "{} for {}".format(monthly_statistic.statistic, monthly_statistic.month),
        )

    def test_unique_together(self):
        """A MonthlyStatistic's Statistic and Month are unique_together."""
        statistic_1 = factories.StatisticFactory(name="Statistic One")
        month_1 = factories.MonthFactory()

        # Create a MonthlyStatistic for statistic_1 and month_1
        factories.MonthlyStatisticFactory(statistic=statistic_1, month=month_1)

        # Attempting to create another MonthlyStatistic for statistic_1 and
        # month_1 raises an error
        with self.assertRaises(IntegrityError):
            factories.MonthlyStatisticFactory(statistic=statistic_1, month=month_1)


class TestExpectedMonthlyCategoryTotal(TestCase):
    def test_str(self):
        """Smoke test for string representation."""
        expected_monthly_total = factories.ExpectedMonthlyCategoryTotalFactory()
        self.assertEqual(
            str(expected_monthly_total),
            "Expected amount for {} in {}".format(
                expected_monthly_total.category, expected_monthly_total.month
            ),
        )

    def test_unique_together(self):
        """A TestExpectedMonthlyCategoryTotal's Cateogry and Month are unique_together."""
        category_1 = factories.CategoryFactory(name="Category One")
        month_1 = factories.MonthFactory()

        # Create a ExpectedMonthlyCategoryTotal for category_1 and month_1
        factories.ExpectedMonthlyCategoryTotalFactory(category=category_1, month=month_1)

        # Attempting to create another ExpectedMonthlyCategoryTotal for category_1
        # and month_1 raises an error
        with self.assertRaises(IntegrityError):
            factories.ExpectedMonthlyCategoryTotalFactory(category=category_1, month=month_1)
