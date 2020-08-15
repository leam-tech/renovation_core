import frappe

def after_migrate():
  set_default_otp_template()

def set_default_otp_template():
  if not frappe.db.get_value("System Settings", None, "email_otp_template"):
    if frappe.db.exists("Email Template", "Default Email OTP Template"):
      # should exists via fixtures
      frappe.db.set_value("System Settings", None, "email_otp_template", "Default Email OTP Template")

  if not frappe.db.get_value("System Settings", None, "sms_otp_template"):
    if frappe.db.exists("SMS Template", "Default SMS OTP Template"):
      # should exists via fixtures
      frappe.db.set_value("System Settings", None, "sms_otp_template", "Default SMS OTP Template")
    