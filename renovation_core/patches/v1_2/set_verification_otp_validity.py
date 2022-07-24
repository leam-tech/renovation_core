import frappe
from frappe.utils import cint
from renovation_core.install.after_sync import set_default_system_settings_default_values


def execute():
    if not cint(frappe.db.get_value("System Settings", fieldname="verification_otp_validity")):
        set_default_system_settings_default_values()
