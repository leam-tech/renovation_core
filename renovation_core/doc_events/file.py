import frappe
from renovation_core.utils.images import after_file_delete, on_file_insert


# onSave, check if image and ask to generate thumbnail
def after_insert(doc, method):
  # thumbnail
  on_file_insert(doc)


def after_delete(doc, method):
  after_file_delete(doc)


def before_insert(doc, method):
  alt = frappe.form_dict.get('alt')
  desc = frappe.form_dict.get('description')
  if alt:
    doc.set('alt', alt)
  if desc:
    doc.set('description', desc)
