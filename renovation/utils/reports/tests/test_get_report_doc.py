from unittest import TestCase
from unittest.mock import patch
from asyncer import runnify

import frappe

import renovation
from renovation.utils.tests import UserFixtures

from .fixtures import ReportFixtures
from ..get_doc import get_report_doc
from ..exceptions import NotFound, PermissionError, ReportDisabled


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
        - Ask for it again and make sure ReportDisabled is raised
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

        #  Ask for it again and make sure ReportDisabled is raised
        with self.assertRaises(ReportDisabled):
            await get_report_doc(_report)

        # Re-enable it
        frappe.db.set_value("Report", _report, "disabled", 0)

    @runnify
    async def test_report_filters(self):
        """
        Make sure filter.default_value gets parsed as intended
        """

        _report_doc = frappe.get_doc(dict(
            doctype="Report",
            name="random-report",
            roles=[dict(role="System Manager")],
            filters=[
                # Today
                dict(
                    fieldname="df1",
                    default_value="{{ frappe.utils.getdate() }}"),
                # Today + 10 days
                dict(
                    fieldname="df2",
                    default_value=(
                        "{{ frappe.utils.add_to_date(date=frappe.utils.getdate(),"
                        " days=10) }}")
                ),
                # No filter defined
                dict(
                    fieldname="df3",
                ),
            ]
        ))

        with patch("frappe.db.exists") as exists_patch:
            exists_patch.return_value = True
            with patch("frappe.get_doc") as get_doc_patch:
                get_doc_patch.return_value = _report_doc

                _report_doc = await get_report_doc(_report_doc.name)

        # Assertion Time!
        from frappe.utils import getdate, add_to_date, get_date_str
        self.assertEqual(
            [x.default_value for x in _report_doc.filters],
            [
                get_date_str(getdate()),
                get_date_str(add_to_date(getdate(), days=10)),
                None,
            ]
        )
