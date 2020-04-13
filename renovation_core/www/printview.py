import frappe
from frappe.www.printview import get_context as _get_content


def get_context(context):
  """Build context for print"""
  if not ((frappe.form_dict.doctype and frappe.form_dict.name) or frappe.form_dict.doc):
    return {
        "body": """<h1>Error</h1>
				<p>Parameters doctype and name required</p>
				<pre>%s</pre>""" % repr(frappe.form_dict)
    }

  if frappe.form_dict.doc:
    doc = frappe.form_dict.doc
  else:
    doc = frappe.get_doc(frappe.form_dict.doctype, frappe.form_dict.name)

  meta = frappe.get_meta(doc.doctype)
  if meta.has_field('is_printed') and not doc.get('is_printed'):
    add_user_printed(doc.doctype, doc.name)
  return _get_content(context)


def add_user_printed(doctype, name):
  return frappe.db.set_value(doctype, name, 'is_printed', 1, update_modified=False)
