from asyncer import asyncify

import renovation


async def get_all_reports():
    roles = renovation.get_roles()

    reports = await asyncify(renovation.local.db.sql)("""
        SELECT
            DISTINCT report.*
        FROM `tabReport` report
        JOIN `tabHas Role` has_role
            ON has_role.parent = report.name AND has_role.parenttype = 'Report'
        WHERE
            has_role.role IN %(roles)s
    """, {"roles": roles}, as_dict=1)

    return reports
