import datetime

import factory
import factory.django
import factory.fuzzy

from django.utils.text import slugify

from .. import models


class CategoryFactory(factory.django.DjangoModelFactory):
    name = factory.fuzzy.FuzzyText()
    slug = factory.LazyAttribute(lambda o: slugify(o.name))

    class Meta:
        model = 'occurrence.Category'


class IncomeCategoryFactory(CategoryFactory):
    type_cat = models.Category.TYPE_EARNING


class ExpenseCategoryFactory(CategoryFactory):
    type_cat = models.Category.TYPE_EXPENSE


class MonthFactory(factory.django.DjangoModelFactory):
    month = factory.fuzzy.FuzzyInteger(low=1, high=12)
    year = factory.fuzzy.FuzzyInteger(low=2000, high=2020)
    name = factory.fuzzy.FuzzyText()
    slug = factory.LazyAttribute(lambda o: slugify(o.name))

    class Meta:
        model = 'occurrence.Month'


class ExpenseTransactionFactory(factory.django.DjangoModelFactory):
    title = factory.fuzzy.FuzzyText()
    slug = factory.LazyAttribute(lambda o: slugify(o.title))
    date = factory.fuzzy.FuzzyDate(
        datetime.date(year=2017, month=1, day=1)
    )
    category = factory.SubFactory(ExpenseCategoryFactory)
    amount = factory.fuzzy.FuzzyDecimal(low=0, high=1000)
    description = factory.fuzzy.FuzzyText()

    class Meta:
        model = 'occurrence.ExpenseTransaction'


class EarningTransactionFactory(factory.django.DjangoModelFactory):
    title = factory.fuzzy.FuzzyText()
    slug = factory.LazyAttribute(lambda o: slugify(o.title))
    date = factory.fuzzy.FuzzyDate(
        datetime.date(year=2017, month=1, day=1)
    )
    category = factory.SubFactory(IncomeCategoryFactory)
    amount = factory.fuzzy.FuzzyDecimal(low=0, high=1000)
    description = factory.fuzzy.FuzzyText()

    class Meta:
        model = 'occurrence.EarningTransaction'


class StatisticFactory(factory.django.DjangoModelFactory):
    name = factory.fuzzy.FuzzyText()
    slug = factory.LazyAttribute(lambda o: slugify(o.name))

    class Meta:
        model = 'occurrence.Statistic'


class MonthlyStatisticFactory(factory.django.DjangoModelFactory):
    statistic = factory.SubFactory(StatisticFactory)
    month = factory.SubFactory(MonthFactory)
    amount = factory.fuzzy.FuzzyDecimal(low=0, high=100000)

    class Meta:
        model = 'occurrence.MonthlyStatistic'


class ExpectedMonthlyCategoryTotalFactory(factory.django.DjangoModelFactory):
    category = factory.SubFactory(CategoryFactory)
    month = factory.SubFactory(MonthFactory)
    amount = factory.fuzzy.FuzzyDecimal(low=0, high=100000)

    class Meta:
        model = 'occurrence.ExpectedMonthlyCategoryTotal'
