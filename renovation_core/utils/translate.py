import frappe
from frappe import _
from frappe.model.document import Document


@frappe.whitelist(allow_guest=True)
def translate_value(values, lang, translateable_kyes=None, key=None):
  if isinstance(values, (dict, Document)):
    if isinstance(values, Document):
      values = values.as_dict()
    for k, val in values.items():
      values[k] = translate_value(val, lang, translateable_kyes, k)
  elif isinstance(values, (list, tuple, set)):
    if isinstance(values, (tuple, set)):
      values = list(values)
    for k, val in enumerate(values):
      values[k] = translate_value(val, lang, translateable_kyes, key)
  elif not (translateable_kyes and key) or key in translateable_kyes:
    values = _(values, lang)
  return values
