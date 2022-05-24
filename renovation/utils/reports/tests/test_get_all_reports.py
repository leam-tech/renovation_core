from unittest import TestCase
from asyncer import runnify

import renovation
from renovation.utils.tests import UserFixtures

from .fixtures import ReportFixtures
from ..get_all_reports import get_all_reports


class TestGetAllReports(TestCase):

    users = UserFixtures()
    reports = ReportFixtures()

    def setUp(self):
        self.users.setUp()
        self.reports.setUp()

    def tearDown(self) -> None:
        renovation.set_user("Administrator")

        self.reports.tearDown()
        self.users.tearDown()

    @runnify
    async def test_admin_get_all(self):
        """
        - Login as Administrator
        - Call get_all_reports
        - Make sure he gets intended reports
        """
        renovation.set_user("Administrator")

        # Call get_all_reports
        reports = await get_all_reports()
        self.assertIsInstance(reports, list)
        self.assertTrue(all(isinstance(x, dict) for x in reports))

        # Make sure he gets intended reports
        report_names = [x.name for x in reports]
        self.assertTrue(all(x in report_names for x in self.reports.STANDARD_REPORTS))

    @runnify
    async def test_system_manager_get_all(self):
        """
        - Login as System Manager
        - Call get_all_reports
        - Make sure he gets intended reports
        """
        # Login as System Manager
        user = self.users.get_user_with_role(["System Manager"], ["Administrator"])
        self.assertNotEqual(user, "Administrator")
        renovation.set_user(user.name)

        # Call get_all_reports
        reports = await get_all_reports()

        # Make sure he gets intended reports
        report_names = [x.name for x in reports]
        expected_reports = self.reports.STANDARD_REPORTS
        # This report is only for few set of Roles. Please refer ./fixtures.py
        expected_reports.remove(self.reports.ADDRESS_AND_CONTACTS)

        self.assertTrue(all(x in report_names for x in expected_reports))

    @runnify
    async def test_website_manager_get_all(self):
        """
        - Login as Website Manager
        - Call get_all_reports
        - He should only get Website Analytics
        """
        # Login as System Manager
        user = self.users.get_user_with_role(["Website Manager"], ["System Manager"])
        self.assertNotEqual(user, "Administrator")
        renovation.set_user(user.name)

        # Call get_all_reports
        reports = await get_all_reports()

        # Make sure he gets intended reports
        report_names = [x.name for x in reports]
        self.assertCountEqual(report_names, [self.reports.WEBSITE_ANALYTICS])
