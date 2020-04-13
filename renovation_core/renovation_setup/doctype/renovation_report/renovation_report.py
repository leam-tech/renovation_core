# -*- coding: utf-8 -*-
# Copyright (c) 2018, Leam Technology Systems and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe.desk.query_report import get_script
from frappe.model.document import Document


class RenovationReport(Document):
  pass


@frappe.whitelist()
def get_defaults_filters(report):
  report = frappe.get_doc("Report", report)
  if report.report_type in ('Query Report', 'Script Report'):
    script = get_script(report.name).get('script')
  else:
    script = [field for field in frappe.get_meta(
        report.ref_doctype).fields if field.get('in_standard_filter')]
  return {
      "is_standard": not report.report_type in ('Query Report', 'Script Report'),
      "script": script
  }
