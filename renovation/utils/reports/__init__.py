from unittest import TestLoader, TestSuite

from .get_all_reports import get_all_reports  # noqa: F401
from .get_report_doc import get_report_doc  # noqa: F401
from .get_report_data import get_report_data  # noqa: F401
from .types import *  # noqa: F401, F403


def load_tests(loader: TestLoader, test_classes, pattern):
    suite = TestSuite()
    _test_classes = []

    from .tests import get_report_tests
    _test_classes.extend(get_report_tests())

    for test_class in _test_classes:
        t = loader.loadTestsFromTestCase(test_class)
        suite.addTests(t)

    return suite
