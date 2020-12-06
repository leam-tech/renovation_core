import frappe


def execute():
  frappe.reload_doctype("SMS Provider")
  sms_settings = frappe.get_doc("SMS Settings", "SMS Settings")
  if sms_settings.sms_gateway_url and not frappe.db.exists("SMS Provider", {"sms_gateway_url": sms_settings.sms_gateway_url}):
    doc = frappe.new_doc("SMS Provider")
    doc.update(sms_settings.as_dict())
    doc.title = sms_settings.name
    doc.doctype = "SMS Provider"
    doc.flags.ignore_permissions = True
    doc.save()
