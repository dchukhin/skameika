from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from .. import models
from . import factories


class CreateMonthlyStatisticsForMonthTestCase(TestCase):
    """Test the 'create_monthlystatistics_for_month' management command."""

    def setUp(self):
        self.stdout = StringIO()
        self.stderr = StringIO()

    def call_command(self, *args, **kwargs):
        kwargs["stdout"] = self.stdout
        kwargs["stderr"] = self.stderr
        call_command("create_monthlystatistics_for_month", *args, **kwargs)

    def test_no_month_slug(self):
        """Calling create_monthlystatistics_for_month without month_slug raises an error."""
        factories.StatisticFactory()
        with self.assertRaises(CommandError) as error:
            self.call_command()
        self.assertEqual(
            str(error.exception),
            "Error: the following arguments are required: month_slug",
        )

    def test_no_months(self):
        """Calling create_monthlystatistics_for_month when no Months exist raises an error."""
        factories.StatisticFactory()
        with self.assertRaises(CommandError) as error:
            self.call_command("")
        self.assertEqual(str(error.exception), 'Month not found for slug ""')

    def test_invalid_month(self):
        """Calling create_monthlystatistics_for_month for an invalid Month raises an error."""
        factories.StatisticFactory()
        with self.assertRaises(CommandError) as error:
            self.call_command(" ")
        self.assertEqual(str(error.exception), 'Month not found for slug " "')

    def test_no_statistics(self):
        """If no Statistics exist, then no MonthlyStatistics are created."""
        month = factories.MonthFactory()
        # There are currently no MonthlyStatistics for the Month.
        self.assertFalse(models.MonthlyStatistic.objects.filter(month=month).exists())

        self.call_command(month.slug)

        # There are still no MonthlyStatistics for the Month.
        self.assertFalse(models.MonthlyStatistic.objects.filter(month=month).exists())

    def test_success(self):
        """Successfully create MonthlyStatistics."""
        month = factories.MonthFactory()
        statistic1 = factories.StatisticFactory()
        statistic2 = factories.StatisticFactory()
        # There are currently no MonthlyStatistics for the Month.
        self.assertFalse(models.MonthlyStatistic.objects.filter(month=month).exists())

        self.call_command(month.slug, **{"amount": 1.23})

        # There are now 2 MonthlyStatistics for the Month.
        self.assertEqual(models.MonthlyStatistic.objects.count(), 2)
        self.assertEqual(models.MonthlyStatistic.objects.filter(month=month).count(), 2)
        self.assertEqual(models.MonthlyStatistic.objects.filter(statistic=statistic1).count(), 1)
        self.assertEqual(models.MonthlyStatistic.objects.filter(statistic=statistic2).count(), 1)
        self.assertEqual(
            list(models.MonthlyStatistic.objects.values_list("amount", flat=True)),
            [Decimal("1.23"), Decimal("1.23")],
        )

    def test_no_amount_defaults_to_0(self):
        """Not passing an 'amount' means that the amount defaults to 0.00."""
        # Create a Month, and a statistic.
        month = factories.MonthFactory()
        factories.StatisticFactory()
        # There are currently no MonthlyStatistics for the Month.
        self.assertFalse(models.MonthlyStatistic.objects.filter(month=month).exists())

        self.call_command(month.slug)

        # The newly-created MonthlyStatistic has an amount of 0.
        self.assertEqual(
            list(models.MonthlyStatistic.objects.values_list("amount", flat=True)),
            [Decimal("0")],
        )
