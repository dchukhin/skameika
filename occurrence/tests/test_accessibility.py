from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.db import connections
from django.shortcuts import reverse

from psycopg2 import OperationalError
from selenium import webdriver
from selenium_axe_python import Axe

from occurrence.tests import factories


class TestAccessibility(StaticLiveServerTestCase):
    def setUp(self):
        super().setUp()
        # Set self.driver to be a headless Firefox browser.
        options = webdriver.FirefoxOptions()
        options.headless = True
        self.driver = webdriver.Firefox(options=options)
        # TODO: fix these errors across the site.
        self.errors_ignored = [
            "Ensures the document has a main landmark",
            "Ensures every form element has a label",
            "Ensures each HTML document contains a non-empty <title> element",
            "Ensures every id attribute value is unique",
            "Ensure that the page, or at least one of its frames contains a level-one heading",
            "Ensures every id attribute value of active elements is unique",
            "Ensures select element has an accessible name",
            "Ensures all page content is contained by landmarks",
        ]

    def close_db_sessions(self, conn):
        """
        Close all database sessions.
        Note: this should automatically happen on teardown, but for some reason
        using Selenium with LiveServerTestCase doesn't automatically close all
        database sessions on teardown, so this method does so explicitly.
        Code based on:
        stackoverflow.com/questions/53323775/database-still-in-use-after-a-selenium-test-in-django
        """
        close_sessions_query = """
            SELECT pg_terminate_backend(pg_stat_activity.pid) FROM pg_stat_activity WHERE
                datname = current_database() AND
                pid <> pg_backend_pid();
        """
        with conn.cursor() as cursor:
            try:
                cursor.execute(close_sessions_query)
            except OperationalError:
                pass

    def test_transactions_list_page(self):
        """Run accessibility tests on the transactions list page."""
        # Create some objects to populate the page.
        for i in range(0, 4):
            factories.ExpenseTransactionFactory()
            factories.EarningTransactionFactory()

        url = self.live_server_url + reverse("transactions")
        self.driver.get(url)

        axe = Axe(self.driver)
        # Inject axe-core javascript into page.
        axe.inject()
        # Run axe accessibility checks.
        results = axe.run()

        # If there are violations, then write them to a file
        if len(results["violations"]) > 0:
            violations_filename = "occurrence/tests/violations_transaction_list.json"
            axe.write_results(results["violations"], violations_filename)
        violations_titles_list = [result["description"] for result in results["violations"]]
        non_ignored_violations = list(set(violations_titles_list) - set(self.errors_ignored))
        violations_titles_str = "\n".join([f"  {title}" for title in non_ignored_violations])
        error_msg = (
            f"\n\nAccessibility violations:\n{violations_titles_str}\n\n"
            f"Violation results have been written to {violations_filename}"
        )
        self.assertEqual(0, len(non_ignored_violations), error_msg)

    def tearDown(self):
        # Quit the browser.
        self.driver.quit()

        # Close all database connections (if they're still open).
        for alias in connections:
            connections[alias].close()
            self.close_db_sessions(connections[alias])

        super().tearDown()
