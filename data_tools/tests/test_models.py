from django.test import TestCase
from data_tools.models import CSVImport


class CSVImportModelTest(TestCase):
    def setUp(self):
        self.csv_import = CSVImport.objects.create(
            file="data_tools/tests/exapmle.csv",
        )

    def test_str_method(self):
        expected_str = (
            f"CSV Import on {self.csv_import.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        self.assertEqual(str(self.csv_import), expected_str)
