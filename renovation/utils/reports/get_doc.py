from asyncer import asyncify

import frappe

import renovation
from .exceptions import PermissionError, NotFound, ReportDisabled


async def get_report_doc(report: str) -> dict:
    """
    Get the report document
    """
    if not await asyncify(frappe.db.exists)("Report", report):
        raise NotFound(report=report)

    report_doc = await asyncify(frappe.get_doc)("Report", report)

    # Validate Permission
    roles = set(renovation.get_roles())
    common_roles = roles.intersection(x.role for x in report_doc.roles)

    if not len(common_roles):
        raise PermissionError(report=report)

    # Validate Disabled
    if report_doc.disabled:
        raise ReportDisabled(report=report)

    for filter in report_doc.filters:
        filter.default_value = parse_default_value(filter.get("default_value"))

    return report_doc


def parse_default_value(template: str):
    """
    Template can have access to all frappe.utils.safe_exec methods
    """
    if not template:
        return None

    return frappe.render_template(template, {})
