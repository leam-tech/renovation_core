from unittest import TestCase
from unittest.mock import patch, AsyncMock
from asyncer import runnify

import frappe
import renovation
from renovation.utils.tests import UserFixtures

from .fixtures import ReportFixtures
from ..get_data import get_report_data
from ..get_doc import get_report_doc
from ..types import ReportColumn, ReportResult


class TestGetReportData(TestCase):

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
    async def test_simple(self):
        """
        - Login as Admin
        - Create a ToDo
        - Ask for report on ToDo
        - Verify columns
        - Verify result
        """
        # Login as Admin
        renovation.set_user("Administrator")
        _report = self.reports.TODO

        # Create a ToDo
        self.reports.add_document(frappe.get_doc(dict(
            doctype="ToDo",
            description="ABCD",
        )).insert())

        # Ask for report on ToDo
        data = await get_report_data(report=_report, filters=dict())
        self.assertIsInstance(data, ReportResult)

        # Verify columns
        self.assertIsInstance(data.columns, list)
        for col in data.columns:
            self.assertIsInstance(col, ReportColumn)
            self.assertTrue(all(
                x in col for x in [
                    "label", "width", "fieldtype", "fieldname"
                ]))

        # Verify result
        self.assertIsInstance(data.result, list)
        self.assertGreater(len(data.result), 0)

    @runnify
    @patch("renovation.utils.reports.get_data.get_report_doc",
           wraps=get_report_doc, new_callable=AsyncMock)
    async def test_get_report_doc_called(self, get_report_doc_mock: AsyncMock):
        """
        - Login as Admin
        - Ask for report
        - Make sure get_report_doc was awaited with report name
        """

        # Login as Admin
        renovation.set_user("Administrator")
        _report = self.reports.TRANSACTION_LOG_REPORT

        # Ask for report
        await get_report_data(report=_report, filters=dict())

        # Make sure get_report_doc was awaited with report name
        get_report_doc_mock.assert_awaited_once_with(report=_report)
