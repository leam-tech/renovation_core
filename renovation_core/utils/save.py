import json

import frappe
from frappe.desk.form.save import savedocs as org_savedocs
from six import string_types


@frappe.whitelist()
def savedocs(doc, action):
  if not isinstance(doc, string_types):
    doc = json.dumps(doc)
  return org_savedocs(doc, action)
