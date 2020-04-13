import json
import traceback

import frappe
from frappe.desk.form.save import set_local_name
from renovation_core.utils import get_request_body, update_http_response
from renovation_core.utils.docdefaults import apply_docdefaults
from six import string_types


def doc_handler(request_method, doctype, name=None):
  if name:
    if request_method == "GET":
      get_doc(doctype, name)  # GET
    elif request_method == "PUT":
      put_doc(doctype, name)
    elif request_method == "DELETE":
      delete_doc(doctype, name)
  elif doctype:
    if request_method == "POST":
      post_doc(doctype)  # POST


def get_doc(doctype, name):
  """
  Builds the response to be sent back
  Fills in with doc data
  """
  try:
    doc = frappe.get_doc(doctype, name)
    if not doc.has_permission("read"):
      raise frappe.PermissionError
    update_http_response({"data": doc.as_dict(), "status": "success"})
  except Exception as ex:
    update_http_response({"data": "failed", "status": "failed",
                          "exception": ex, "traceback": traceback.format_exc()})


def post_doc(doctype):
  try:
    # if modifying, update save_submit_doc too
    # fetch defaults here and update
    data = frappe._dict(get_request_body_doc())
    apply_docdefaults(data, data, doctype)

    doc = frappe.new_doc(doctype)
    # update doctype field since it wont be passed in data
    doc.update(data)
    doc.insert()

    apply_docdefaults(doc, doc, doctype, evaluation_time="After Save")
    doc.save()

    # check submittable
    # check_submittable(doc, "submit")

    frappe.db.commit()

    update_http_response({"data": doc.as_dict(), "status": "success"})
  except Exception as ex:
    frappe.db.rollback()
    update_http_response({"data": "failed", "status": "failed",
                          "exception": ex, "traceback": traceback.format_exc()})


def delete_doc(doctype, name):
  try:
    # TODO
    # Decide if on delete
    doc = frappe.get_doc(doctype, name)
    # check_submittable(doc, "cancel")
    doc.delete()

    frappe.db.commit()

    update_http_response({"status": "success"})
  except Exception as ex:
    frappe.db.rollback()
    update_http_response({"data": "failed", "status": "failed",
                          "exception": ex, "traceback": traceback.format_exc()})


def put_doc(doctype, name):
  """
  DELETE Existing, PUT UP NEW
  ----------------
  Submitted -> Cancelled
  Amend -> New DOC
  Return the new name
          renovation points to -> SINV-00001-1
  """
  try:
    doc = frappe.get_doc(doctype, name)
    if frappe.get_meta(doctype).is_submittable and 1 == 2:
      check_submittable(doc, "cancel")
      new_doc = frappe.copy_doc(doc)
      new_doc.update(get_request_body_doc())
      new_doc.amended_from = doc.name
      new_doc.status = "Draft"
      new_doc.insert()

      check_submittable(new_doc, "submit")
      doc = new_doc
    else:
      doc.update(get_request_body_doc())
      # mandatory call before saving for new __islocal docs
      set_local_name(doc)
      doc.save()

    frappe.db.commit()

    update_http_response({"data": doc.as_dict(), "status": "success"})
  except Exception as ex:
    frappe.db.rollback()
    update_http_response({"data": "failed", "status": "failed",
                          "exception": ex, "traceback": traceback.format_exc()})


@frappe.whitelist()
def save_submit_doc(doc, submit=True):
  if isinstance(doc, string_types):
    doc = json.loads(doc)
  data = frappe._dict(doc)
  if data.name and frappe.db.exists(data.doctype, data.name):
    frappe.throw("Doc Exists Already")
    """
		_doc = frappe.get_doc(doc.doctype, doc.name)
		_doc.update(doc)
		"""

  # if modifying, update post_doc too
  # fetch defaults here and update
  apply_docdefaults(data, data, data.doctype)

  doc = frappe.new_doc(data.doctype)
  # update doctype field since it wont be passed in data
  doc.update(data)
  doc.insert()

  apply_docdefaults(doc, doc, data.doctype, evaluation_time="After Save")
  doc.save()
  if submit:
    doc.submit()
  return doc.as_dict()


def check_submittable(doc, action="submit"):
  """
  if docstatus = 0; we are about to submit; else cancel
  """
  d_meta = frappe.get_meta(doc.doctype)
  if not d_meta.is_submittable:
    return

  if doc.docstatus == 0 and action == "submit":
    doc.submit()
  elif doc.docstatus == 1 and action == "cancel":
    doc.cancel()


def get_request_body_doc():
  return get_request_body(as_json=True).get('doc')
