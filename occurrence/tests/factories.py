import datetime

import factory
import factory.django
import factory.fuzzy

from django.utils.text import slugify


class CategoryFactory(factory.django.DjangoModelFactory):
    name = factory.fuzzy.FuzzyText()
    slug = factory.LazyAttribute(lambda o: slugify(o.name))

    class Meta:
        model = 'occurrence.Category'


class MonthFactory(factory.django.DjangoModelFactory):
    month = factory.fuzzy.FuzzyInteger(low=1, high=12)
    year = factory.fuzzy.FuzzyInteger(low=2000, high=2020)
    name = factory.fuzzy.FuzzyText()

    class Meta:
        model = 'occurrence.Month'


class TransactionFactory(factory.django.DjangoModelFactory):
    title = factory.fuzzy.FuzzyText()
    slug = factory.LazyAttribute(lambda o: slugify(o.title))
    date = factory.fuzzy.FuzzyDate(
        datetime.date(year=2017, month=1, day=1)
    )
    month = factory.SubFactory(MonthFactory)
    category = factory.SubFactory(CategoryFactory)
    amount = factory.fuzzy.FuzzyDecimal(low=0, high=1000)
    description = factory.fuzzy.FuzzyText()

    class Meta:
        model = 'occurrence.Transaction'
