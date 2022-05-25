from asyncer import asyncify

import frappe

import renovation
from .exceptions import PermissionError, NotFound


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

    return report_doc
