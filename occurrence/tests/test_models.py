from datetime import date

from django.test import TestCase

from . import factories
from .. import models


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
        cat_order_1_name_a2 = factories.CategoryFactory(order=1, name='a2')
        cat_order_2_name_a1 = factories.CategoryFactory(order=2, name='a1')
        cat_order_1_name_b2 = factories.CategoryFactory(order=1, name='b2')
        cat_order_2_name_b1 = factories.CategoryFactory(order=2, name='b1')

        with self.subTest('Categories with same order are ordered by name'):
            qs = models.Category.objects.filter(
                id__in=[cat_order_1_name_b2.id, cat_order_1_name_a2.id]
            )
            self.assertEqual(
                set(qs.values_list('id', flat=True)),
                set([cat_order_1_name_a2.id, cat_order_1_name_b2.id])
            )

        with self.subTest('all Categories'):
            self.assertEqual(
                set(models.Category.objects.all().values_list('id', flat=True)),
                set(
                    [cat_order_1_name_a2.id, cat_order_1_name_b2.id,
                     cat_order_2_name_a1.id, cat_order_2_name_b1.id]
                )
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
            self.assertIsNotNone(category.id, )


class TestMonth(TestCase):
    def test_str(self):
        """Smoke test for string representation."""
        month = factories.MonthFactory()
        self.assertEqual(str(month), month.name)


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
            '{} - {}'.format(
                transaction.title,
                transaction.date.strftime('%Y-%m-%d')
            )
        )

    def test_save_unique_slug(self):
        """Saving a Transaction gives it a unique slug."""
        with self.subTest('First Transaction'):
            # Currently, there are no Transactions
            self.assertEqual(self.model_class.objects.count(), 0)
            transaction1 = self.factory()
            # Now there is 1 Transaction
            self.assertEqual(self.model_class.objects.count(), 1)

        with self.subTest('Second Transaction with same slug'):
            transaction2 = self.factory(slug=transaction1.slug)
            # Now there are 2 Transactions, and their slugs are unique
            self.assertEqual(self.model_class.objects.count(), 2)
            self.assertNotEqual(transaction2.slug, transaction1.slug)

        with self.subTest('Third Transaction with same slug'):
            transaction3 = self.factory(slug=transaction1.slug)
            # Now there are 3 Transactions, and their slugs are unique
            self.assertEqual(self.model_class.objects.count(), 3)
            self.assertNotEqual(transaction3.slug, transaction1.slug)

    def save_slug_already_unique(self):
        """Saving a Transaction with a slug that is already unique keeps its slug."""
        unique_slug = 'uniqueslug'
        # A transaction with a unique slug
        transaction1 = self.factory(slug=unique_slug)
        # A second transaction with the same title and date as transaction1
        self.factory(title=transaction1.title, date=transaction1.date)

        # Now saving transaction1 should keep its slug, rather than changing it
        # to something new
        transaction1.save()
        self.assertEqual(transaction1.slug, unique_slug)

    def test_save_associate_month(self):
        """Saving a Transaction without a Month associates it with correct Month."""
        with self.subTest('new Transaction with no associated month; no Month object'):
            test_date = date(year=2017, month=5, day=1)
            transaction1 = self.factory(date=test_date, month=None)
            # The transaction1 now has the correct month
            self.assertEqual(transaction1.month.name, test_date.strftime('%B, %Y'))
            may_2017_month = transaction1.month

        with self.subTest('new Transaction with no associated month; Month object exists'):
            # Now the Month for the test_date exists (may_2017_month). The next
            # Transaction in May, 2017 should be associated with it
            transaction2 = self.factory(date=test_date, month=None)
            # The transaction2 now has the correct month
            self.assertEqual(transaction2.month, may_2017_month)

        with self.subTest('new Transaction with associated month'):
            transaction3 = self.factory(date=test_date, month=may_2017_month)
            # The transaction3 is still associated with may_2017_month
            self.assertEqual(transaction3.month, may_2017_month)

        with self.subTest('Transaction associated with wrong Month'):
            june_2017_month = factories.MonthFactory(month=6, year=2017, name='June, 2017')
            transaction3.month = june_2017_month
            transaction3.save()
            # The transaction3 is now associated with may_2017_month
            self.assertEqual(transaction3.month, may_2017_month)

        with self.subTest('changing Transaction date associates it with correct Month'):
            # Currently, transaction3 is associated with may_2017_month
            self.assertEqual(transaction3.month, may_2017_month)
            # Change the transaction3 date to be in June, 2017
            transaction3.date = date(year=2017, month=6, day=15)
            transaction3.save()
            # Now, transaction3 is associated with june_2017_month
            self.assertEqual(transaction3.month, june_2017_month)


class TestExpenseTransaction(TestCase, TransactionBaseMixin):
    model_class = models.ExpenseTransaction
    factory = factories.ExpenseTransactionFactory


class TestEarningTransaction(TestCase, TransactionBaseMixin):
    model_class = models.EarningTransaction
    factory = factories.EarningTransactionFactory
