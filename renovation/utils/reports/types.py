from typing import Any, List
from enum import Enum

import renovation


class ReportElementFieldType(Enum):
    CHECK = "Check"
    CURRENCY = "Currency"
    DATA = "Data"
    DATE = "Date"
    DATETIME = "Datetime"
    DYNAMIC = "Dynamic"
    FLOAT = "Float"
    FOLD = "Fold"
    INT = "Int"
    LINK = "Link"
    SELECT = "Select"
    TIME = "Time"


class ReportColumn(renovation._dict):
    fieldname: str
    label: str
    fieldtype: str
    options: str
    width: int


class ReportResult(renovation._dict):
    result: List[List[Any]]
    columns: List[ReportColumn]
    add_total_row: bool
