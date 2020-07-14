import frappe

def execute():
  df = frappe.db.get_value("Custom Field", {"fieldname": "renovation_sms_pin", "dt": "User"})
  if not df:
    return
  
  frappe.delete_doc("Custom Field", df, force=1)