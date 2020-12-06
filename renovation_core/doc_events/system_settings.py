import frappe


def on_change(doc, method):
  from ..utils.logging import update_cache
  update_cache()


def before_update(doc, method):
  if doc.get("sms_settings") and not frappe.db.get_value('SMS Settings', None, 'sms_gateway_url'):
    provider = frappe.get_doc("SMS Provider", doc.get("sms_settings"))
    sms_settings = frappe.get_single("SMS Settings")
    data = provider.as_dict()
    del data["name"]
    del data["doctype"]
    sms_settings.update(data)
    sms_settings.flags.ignore_permissions = True
    sms_settings.save()
