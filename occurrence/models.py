from datetime import date

from django.db import models
from django.utils.text import slugify


class Category(models.Model):
    TYPE_INCOME = 'income'
    TYPE_EXPENSE = 'expense'
    TYPE_CHOICES = (
        (TYPE_INCOME, 'Income'),
        (TYPE_EXPENSE, 'Expense'),
    )

    # The different ways to have totals for Categories. Most Categories will use
    # the regular type, but some will use a running type
    TOTAL_TYPE_REGULAR = 'regular'
    TOTAL_TYPE_RUNNING = 'running'
    TOTAL_TYPE_CHOICES = (
        (TOTAL_TYPE_REGULAR, 'Regular total'),
        (TOTAL_TYPE_RUNNING, 'Running total'),
    )

    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(unique=True)
    type_cat = models.CharField(max_length=20, choices=TYPE_CHOICES, default=TYPE_EXPENSE)
    total_type = models.CharField(
        max_length=20,
        choices=TOTAL_TYPE_CHOICES,
        default=TOTAL_TYPE_REGULAR,
        help_text='When finding totals for this Category, how should the totals '
                  'be displayed? Some Categories may need to be excluded from '
                  'the totals, and be displayed on their own page.',
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ('name', )


class Month(models.Model):
    """
    A month of time.

    We could avoid having this model, since the data is already in the Transaction
    model, but having it makes calculations of Transactions, etc. by month faster.
    """
    month = models.PositiveSmallIntegerField()
    year = models.PositiveSmallIntegerField()
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)

    def __str__(self):
        """Return the name of the Month."""
        return self.name

    class Meta:
        ordering = ('-year', '-month', )


class TransactionBase(models.Model):
    """An abstract base model for Transaction-like models."""
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    date = models.DateField(default=date.today)
    month = models.ForeignKey(
        Month,
        blank=True,
        help_text="The month that this Transaction occurred in.",
        on_delete=models.PROTECT  # Don't allow a Month to be deleted if it has Transactions
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.CharField(max_length=255, blank=True)
    receipt = models.ImageField(upload_to='transaction_receipts/', blank=True)

    def __str__(self):
        """Return the title and date of the Transaction."""
        return '{} - {}'.format(
            self.title,
            self.date.strftime('%Y-%m-%d')
        )

    def save(self, *args, **kwargs):
        """Make sure the slug field is unique, and associate with a Month."""
        # Create a potential_slug based on title and self.date (including year,
        # month, day)
        potential_slug = '{}-{}'.format(
            slugify(self.title),
            self.date.strftime('%Y-%m-%d')
        )
        # Does a Transaction with this slug already exist?
        if self.__class__.objects.filter(slug=potential_slug).exists():
            # Find all the slugs that are similar to this potential_slug
            similar_slugs = self.__class__.objects.filter(
                slug__icontains=potential_slug
            ).values_list('slug')
            potential_slug += '_2'
            i = 2
            # Continue to increase the number at the end of potential_slug until
            # we get a unique slug
            while potential_slug in similar_slugs:
                potential_slug = potential_slug[0:-1] + str(i)
                i += 1
        # This is a unique slug, so set it to self.slug
        self.slug = potential_slug

        # Try to find a Month for this Transaction's date
        try:
            month = Month.objects.get(month=self.date.month, year=self.date.year)
        except Month.DoesNotExist:
            # A Month for this Transaction's date does not exist, so create one
            month = Month.objects.create(
                month=self.date.month,
                year=self.date.year,
                name=self.date.strftime('%B, %Y'),
                slug=slugify(self.date.strftime('%B, %Y')),
            )
        # Associate this Transaction with the correct Month for its date
        self.month = month

        super().save(*args, **kwargs)

    class Meta:
        abstract = True


class ExpenseTransaction(TransactionBase):
    """Model for tracking (expense) transactions that occur."""
    category = models.ForeignKey(
        Category,
        limit_choices_to={'type_cat': Category.TYPE_EXPENSE}
    )
    pending = models.BooleanField(default=False)

    class Meta:
        ordering = ('-date', )


class EarningTransaction(TransactionBase):
    """Model for tracking income transactions that occur."""
    category = models.ForeignKey(
        Category,
        limit_choices_to={'type_cat': Category.TYPE_INCOME}
    )

    class Meta:
        ordering = ('-date', )
