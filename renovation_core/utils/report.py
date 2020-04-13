import frappe
from frappe.desk.query_report import run as query_report
from renovation_core.utils import get_request_body, update_http_response
from six import string_types


def get_report():
  req = frappe._dict(get_request_body(as_json=True))
  if not req.get("report"):
    frappe.throw("No report specified")

  report = frappe.get_doc("Report", req.report)

  out = {}
  if report.report_type in ["Query Report", "Script Report"]:
    out = query_report(req.report, req.filters, req.user)
  elif report.report_type in ["Report Builder"]:
    out = {"report_type": "Report Builder"}
  else:
    frappe.throw("Invalid report type")

  out["columns"] = objectify_columns(out.get("columns"))
  out["result"] = array_result(out.get("columns"), out.get("result"))
  update_http_response(out)


def array_result(columns, result):
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
  cols = []

  for strcol in columns:
    if not isinstance(strcol, string_types):
      cols.append(strcol)
      continue

    label, type, width = strcol.split(':')

    options = None
    if '/' in type:
      type, options = type.split('/')

    cols.append({
        "label": label,
        "type": type,
        "width": width,
        "options": options,
        "fieldname": frappe.scrub(label)
    })

  return cols
