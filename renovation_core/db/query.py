import json

import frappe
from six import string_types

try:
  from renovation_core.db.db_query import UpdatedDBQuery, update_transalte
except ImportError:
  from .db_query import UpdatedDBQuery


@frappe.whitelist(allow_guest=True)
def get_list_with_child(doctype, *args, **kwargs):
  """Uncomment this in the future
  While fetching Related Docs in renovation, we wont know the parent names..
  if frappe.is_table(doctype) and kwargs.get("fields"):
          check_parent_permission(parent)"""
  user_lang = frappe.get_request_header('Accept-Language')
  if user_lang:
    frappe.local.lang = user_lang.split('-')[0]

  if "cmd" in kwargs:
    del kwargs["cmd"]
  """get_list with child table are to be supported here
	kwargs.table_fields = {
		items: []
		taxes: []
	}"""
  if "table_fields" in kwargs:

    def get_child_dt(p_dt, table_fieldname):
      """
      Returns the child doctype for the fieldname
      """
      child_dt = frappe.db.get_value("DocField", filters={
          "parent": p_dt, "fieldname": table_fieldname}, fieldname="options")
      if not child_dt:
        child_dt = frappe.db.get_value("Custom Field", filters={
            "dt": p_dt, "fieldname": table_fieldname}, fieldname="options")
      if not child_dt:
        frappe.throw("Invalid child fieldname {}: {}".format(
            p_dt, table_fieldname))
      return child_dt

    if kwargs.get("fields"):
      kwargs["fields"] = kwargs["fields"] + ", name"

    table_fields = kwargs["table_fields"]
    if isinstance(table_fields, string_types):
      table_fields = json.loads(table_fields)

    del kwargs["table_fields"]

    ret = []
    for m in UpdatedDBQuery(doctype).execute(None, *args, **kwargs):
      for fieldname, fields in table_fields.items():
        child_dt = get_child_dt(doctype, fieldname)
        m[fieldname] = frappe.get_list(child_dt, filters={
            "parenttype": doctype, "parent": m.name, "parentfield": fieldname}, fields=fields, order_by="idx")
        if frappe.local.lang != 'en':
          m[fieldname] = update_transalte(child_dt, m[fieldname])
      ret.append(m)

    return ret
  else:
    return UpdatedDBQuery(doctype).execute(None, *args, **kwargs)


def _get_fields(fields=None):
  if not fields:
    return "name"
  elif isinstance(fields, (tuple, list)):
    if "name" not in fields:
      if isinstance(fields, tuple):
        fields = list(fields)
      fields = fields.append("name")
    return fields
  elif isinstance(fields, string_types):
    if fields == "*":
      return fields
    else:
      fields = frappe.parse_json(fields) if fields.startswith(
          "[") else fields.split(",")
    if "name" not in fields:
      fields.append("name")
    return fields
  else:
    return "name"
