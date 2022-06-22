from .test_get_all_reports import TestGetAllReports
from .test_get_report_doc import TestGetReportDoc
from .test_get_report_data import TestGetReportData


def get_report_tests():
    return [
        TestGetAllReports,
        TestGetReportDoc,
        TestGetReportData
    ]
