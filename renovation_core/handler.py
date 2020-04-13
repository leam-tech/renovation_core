import re

import frappe
from frappe.handler import uploadfile as uf

from .utils import get_request_method, get_request_path, update_http_response
from .utils.auth import generate_sms_pin, verify_sms_pin
from .utils.doc import doc_handler
from .utils.report import get_report


# api generals are handled here
# this file will be the interface to the frappe system
# if frappe system was to make changes in the future, we will have to update it here only


@frappe.whitelist(allow_guest=True)
def handler():

  request_parts = get_request_path()[1:].split("/")
  request_method = get_request_method()
  if request_parts[3] == "doc":
    doc_handler(request_method, request_parts[4], '/'.join(request_parts[5:]))
  elif request_parts[3] == "session":
    get_session()
  elif request_parts[3] == "report":
    get_report()
  elif request_parts[3] == "auth.sms.generate":
    generate_sms_pin()
  elif request_parts[3] == "auth.sms.verify":
    verify_sms_pin()
  elif request_parts[3] == "test":
    print(request_parts[3])
    print("FORM DICT :")
    print(frappe.form_dict)
  else:
    return "Not Implemented"


def get_session():
  try:
    boot = frappe.sessions.get()
    boot_json = frappe.as_json(boot)
    # remove script tags from boot
    boot_json = re.sub(r"\<script\>[^<]*\</script\>", "", boot_json)
    update_http_response({"data": boot_json, "status": "success"})
  except Exception:
    update_http_response({"status": "failed"})
    print(frappe.get_traceback())


@frappe.whitelist(allow_guest=True)
def uploadfile():
  ret = uf()

  # We dont want to auto save the doc on file upload

  # form = frappe.form_dict
  # if ret and ret.get("file_url", None) and form and form.get("doctype", None) and form.get("docname") and form.get("docfield", None):
  # 	# fill the field
  # 	dt = form.get("doctype")
  # 	dn = form.get("docname")
  # 	df = form.get("docfield")
  # 	if frappe.db.get_value(dt, dn):
  # 		frappe.db.set_value(dt, dn, df, ret.get("file_url"))
  return ret
