import frappe
from frappe.utils import cint


def after_sync():
    set_default_system_settings_default_values()


def set_default_system_settings_default_values():
    meta = frappe.get_meta("System Settings")
    df = meta.get_field("verification_otp_validity")
    frappe.db.set_value("System Settings", "System Settings", "verification_otp_validity",
                        cint(df.default))
