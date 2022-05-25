from typing import List, Union
from asyncer import asyncify

import frappe
import renovation

from .get_doc import get_report_doc
from .types import ReportColumn, ReportResult


async def get_report_data(report: str, filters: Union[List[dict], dict]) -> ReportResult:
    """
    Async wrapper around Frappe's report runner

    :report (str): The name of the report to execute
    :filters (str): set of filters to use for execution
    """
    from frappe.desk.query_report import run as query_report

    # All required validations should happen here
    report = await get_report_doc(report=report)

    data = {}
    if report.report_type in ["Query Report", "Script Report"]:
        data = await asyncify(query_report)(report_name=report.name, filters=filters)
    elif report.report_type in ["Report Builder"]:
        data = {"report_type": "Report Builder"}
    else:
        frappe.throw("Invalid report type")

    data["columns"] = objectify_columns(data.get("columns"))
    data["result"] = array_result(data.get("columns"), data.get("result"))

    return ReportResult(data)


def array_result(columns, result):
    """
    Results from reports can either be List[List[str]] or List[dict] with column name as keys
    We unify it to be an List[List[str]] here
    """
    if not result or len(result) == 0:
        return result

    if isinstance(result[0], (list, tuple)):
        return result

    out = []
    for obj in result:
        row = []
        for col in columns:
            row.append(obj.get(col.get("fieldname")) or '')
        out.append(row)
    return out


def objectify_columns(columns):
    """
    Columns returned from different reports can either be
    dicts or str

    eg:
    - dict { label, type, width, fieldname }
    - str: "label:type:width"
        for link fields, it could be: "label:Link/User:width"
    """
    cols = []

    for col in columns:
        if isinstance(col, str):
            label, type, width = col.split(':')
            options = None
            if '/' in type:
                type, options = type.split('/')

            col = renovation._dict({
                "label": label,
                "fieldtype": type,
                "width": width,
                "options": options,
            })

        for k in ["label", "fieldtype", "width", "options", "fieldname"]:
            if k in col:
                continue
            col[k] = None

        if not col.fieldname:
            col.fieldname = frappe.scrub(label)

        col = ReportColumn(col)
        cols.append(col)

    return cols
