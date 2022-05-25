from unittest import TestCase
from asyncer import runnify
import frappe

import renovation
from renovation.utils.tests import UserFixtures

from .fixtures import ReportFixtures
from ..get_report_doc import get_report_doc
from ..exceptions import NotFound, PermissionError


class TestGetReportDoc(TestCase):

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
    async def test_admin_get_doc(self):
        """
        - Login as Administrator
        - Call get_report_doc
        - Make sure he gets the whole report doc
        """
        renovation.set_user("Administrator")

        # Call get_report_doc
        _report_name = self.reports.TRANSACTION_LOG_REPORT
        report = await get_report_doc(_report_name)

        # Make sure he gets the whole report doc
        self.assertIsNotNone(report)
        self.assertEqual(report.doctype, "Report")
        self.assertEqual(report.name, _report_name)

        _fields = ["ref_doctype", "report_type", "add_total_row", "disabled", "roles"]
        report = report.as_dict()
        self.assertTrue(all(x in report for x in _fields))

    @runnify
    async def test_website_manager_ask_for_restricted_report(self):
        """
        - Login as Website Manager
        - Call get_report_doc on TRANSACTION_LOG_REPORT (restricted)
        - Make sure PermissionError is raised
        """
        # Login as System Manager
        user = self.users.get_user_with_role(["Website Manager"], ["System Manager"])
        self.assertNotEqual(user, "Administrator")
        renovation.set_user(user.name)
        _report = self.reports.TRANSACTION_LOG_REPORT

        # Call get_report_doc
        with self.assertRaises(PermissionError):
            await get_report_doc(_report)

    @runnify
    async def test_asking_for_non_existent_report(self):
        """
        - Login as Admin
        - Ask for Non-existent report and get NotFound EXC
        """
        # Login as Admin
        renovation.set_user("Administrator")

        # Ask for Non-existent report and get NotFound EXC
        with self.assertRaises(NotFound):
            await get_report_doc("non-existent-report")

    @runnify
    async def test_disabled_report(self):
        """
        - Login as Administrator
        - Ask for report doc
        - Make sure report to be disabled is obtained
        - Disable the report
        - Ask for it again
        - Make sure disabled-report is obtained as previously
        - Re-enable it
        """

        # Login as Administrator
        renovation.set_user("Administrator")
        _report = self.reports.TRANSACTION_LOG_REPORT

        # Ask for report doc
        report_doc = await get_report_doc(_report)

        # Make sure report to be disabled is obtained
        self.assertIsNotNone(report_doc)
        self.assertEqual(report_doc.doctype, "Report")
        self.assertEqual(report_doc.name, _report)

        # Disable the report
        frappe.db.set_value("Report", _report, "disabled", 1)

        # Ask for it again
        report_doc = await get_report_doc(_report)

        # Make sure disabled-report is obtained as previously
        self.assertIsNotNone(report_doc)
        self.assertEqual(report_doc.doctype, "Report")
        self.assertEqual(report_doc.name, _report)

        # Re-enable it
        frappe.db.set_value("Report", _report, "disabled", 0)
