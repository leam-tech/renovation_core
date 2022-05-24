from typing import Any, List
import renovation


class ReportColumn:
    fieldname: str
    label: str
    fieldtype: str
    options: str
    width: int


class ReportResult(renovation._dict):
    result: List[List[Any]]
    columns: List[ReportColumn]
