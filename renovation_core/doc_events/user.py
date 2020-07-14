import frappe
from frappe.utils.password import update_password


def before_save(doc, method):
  doc.__new_quick_login_pin = doc.quick_login_pin
  doc.quick_login_pin = ""

  old_value = doc.db_get('override_as_global')
  if old_value != doc.override_as_global:
    for k in frappe.cache().hkeys("renovation_doc_bundle") or []:
      if k.endswith(":{}".format(doc.name)):
        frappe.cache().hdel("renovation_doc_bundle", k)


def on_update(doc, method):
  update_quick_login_pin(doc, doc.__new_quick_login_pin)


def update_quick_login_pin(doc, quick_login_pin):
  if not quick_login_pin:
    return

  update_password(doc.name, quick_login_pin, doctype=doc.doctype,
                  fieldname='quick_login_pin', logout_all_sessions=False)
