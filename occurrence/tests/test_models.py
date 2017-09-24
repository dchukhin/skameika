from django.test import TestCase

from . import factories
from .. import models


class TestCategory(TestCase):
    def test_str(self):
        """Smoke test for string representation."""
        category = factories.CategoryFactory()
        self.assertEqual(str(category), category.name)


class TestMonth(TestCase):
    def test_str(self):
        """Smoke test for string representation."""
        month = factories.MonthFactory()
        self.assertEqual(str(month), month.name)


class TestTransaction(TestCase):
    def test_str(self):
        """Smoke test for string representation."""
        transaction = factories.TransactionFactory()
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
            self.assertEqual(models.Transaction.objects.count(), 0)
            transaction1 = factories.TransactionFactory()
            # Now there is 1 Transaction
            self.assertEqual(models.Transaction.objects.count(), 1)

        with self.subTest('Second Transaction with same slug'):
            transaction2 = factories.TransactionFactory(slug=transaction1.slug)
            # Now there are 2 Transactions, and their slugs are unique
            self.assertEqual(models.Transaction.objects.count(), 2)
            self.assertNotEqual(transaction2.slug, transaction1.slug)

        with self.subTest('Third Transaction with same slug'):
            transaction3 = factories.TransactionFactory(slug=transaction1.slug)
            # Now there are 3 Transactions, and their slugs are unique
            self.assertEqual(models.Transaction.objects.count(), 3)
            self.assertNotEqual(transaction3.slug, transaction1.slug)
