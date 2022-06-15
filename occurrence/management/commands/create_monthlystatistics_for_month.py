from django.core.management.base import BaseCommand, CommandError
from occurrence.models import Month, MonthlyStatistic, Statistic


class Command(BaseCommand):
    help = 'Creates MonthlyStatistics for a Month'

    def add_arguments(self, parser):
        parser.add_argument('month_slug', type=str)
        parser.add_argument('--amount', type=float, default=0.0, required=False)

    def handle(self, *args, **options):
        """
        Create MonthlyStatistics for a Month.

        We:
         - find the appropriate Month
         - loop over each of the Statistics, and create one for the Month
        """
        month_slug = options['month_slug']
        month = Month.objects.filter(slug=month_slug).first()
        amount = options['amount']

        # If the Month was not found, then raise an error.
        if not month:
            raise CommandError('Month not found for slug "%s"' % month_slug)

        # Loop over each of the Statistics, and create one for the month.
        objects_created = []
        for statistic in Statistic.objects.all():
            objects_created.append(
                MonthlyStatistic.objects.create(month=month, statistic=statistic, amount=amount)
            )

        # Write a success message of the MonthlyStatistic that were created.
        objects_created_str = '\n'.join(["    " + str(obj) for obj in objects_created])
        self.stdout.write(self.style.SUCCESS('Successfully created:\n%s') % objects_created_str)
