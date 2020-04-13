import frappe


def validate_api_key_secret(api_key, api_secret):
  user = frappe.db.get_value(
      doctype="User",
      filters={"api_key": api_key},
      fieldname=['name']
  )
  form_dict = frappe.local.form_dict
  user_secret = frappe.utils.password.get_decrypted_password(
      "User", user, fieldname='api_secret')
  if api_secret == user_secret:
    # frappe.set_user(user)
    from frappe.auth import LoginManager
    login = LoginManager()
    login.check_if_enabled(user)
    login.login_as(user)
    frappe.local.form_dict = form_dict
