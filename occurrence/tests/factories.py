import datetime

import factory
import factory.django
import factory.fuzzy

from django.utils import timezone
from django.utils.text import slugify


class CategoryFactory(factory.django.DjangoModelFactory):
    name = factory.fuzzy.FuzzyText()
    slug = factory.LazyAttribute(lambda o: slugify(o.name))

    class Meta:
        model = 'occurrence.Category'


class TransactionFactory(factory.django.DjangoModelFactory):
    title = factory.fuzzy.FuzzyText()
    slug = factory.LazyAttribute(lambda o: slugify(o.title))
    date = factory.fuzzy.FuzzyDateTime(
        timezone.datetime(year=2017, month=1, day=1, tzinfo=timezone.pytz.utc)
    )
    category = factory.SubFactory(CategoryFactory)
    description = factory.fuzzy.FuzzyText()

    class Meta:
        model = 'occurrence.Transaction'
