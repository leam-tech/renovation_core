import frappe
from frappe.integrations.oauth2 import openid_profile


@frappe.whitelist()
def openid_profile_endpoint(*args, **kwargs):
  openid_profile(*args, **kwargs)
  frappe.local.response['verified'] = True
