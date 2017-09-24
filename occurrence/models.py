from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class Category(models.Model):
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ('name', )


class Transaction(models.Model):
    """Model for tracking transactions that occur."""
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    date = models.DateTimeField(default=timezone.now)
    category = models.ForeignKey(Category)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.CharField(max_length=255, blank=True)
    receipt = models.ImageField(upload_to='transaction_receipts/', blank=True)
    pending = models.BooleanField(default=False)

    def __str__(self):
        """Return the title and date of the Transaction, in the settings.TIME_ZONE."""
        settings_tz = timezone.pytz.timezone(settings.TIME_ZONE)
        return '{} - {}'.format(
            self.title,
            self.date.astimezone(settings_tz).strftime('%Y-%m-%d %H:%M:%S')
        )

    def save(self, *args, **kwargs):
        """Make sure the slug field is unique, then continue saving."""
        # Create a potential_slug based on title and self.date (including year,
        # month, day, hour, minute, second)
        potential_slug = '{}-{}'.format(
            slugify(self.title),
            self.date.strftime('%Y-%m-%d-%H-%M-%S')
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
        super().save(*args, **kwargs)
