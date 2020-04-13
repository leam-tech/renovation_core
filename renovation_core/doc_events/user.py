import frappe


def before_save(doc, method):
  old_value = doc.db_get('override_as_global')
  if old_value != doc.override_as_global:
    for k in frappe.cache().hkeys("renovation_doc_bundle") or []:
      if k.endswith(":{}".format(doc.name)):
        frappe.cache().hdel("renovation_doc_bundle", k)
