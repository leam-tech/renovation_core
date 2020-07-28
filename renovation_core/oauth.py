import json

import frappe
from frappe import _
from frappe.integrations.oauth2_logins import decoder_compat
from frappe.utils.oauth import get_oauth2_authorize_url, get_email, update_oauth_user, SignupDisabledError, \
  get_info_via_oauth
from six import string_types


@frappe.whitelist(allow_guest=True)
def get_oauth_url(provider: str, redirect_to: str) -> str:
  return get_oauth2_authorize_url(provider, redirect_to)


@frappe.whitelist(allow_guest=True)
def login_via_google(code, state=None, login=True, use_jwt=False):
  frappe.form_dict['use_jwt'] = use_jwt
  return login_via_oauth2('google', code=code, state=state, decoder=decoder_compat, login=login)


def login_via_oauth2(provider, code, state, decoder=None, login=True):
  info = get_info_via_oauth(provider, code, decoder)
  return login_oauth_user(info, provider=provider, state=state, login=login)


def login_oauth_user(data=None, provider=None, state=None, login=True):
  if isinstance(data, string_types):
    data = json.loads(data)

  user = get_email(data)

  if not user:
    frappe.throw(_("Please ensure that your profile has an email address"))

  try:
    if update_oauth_user(user, data, provider) is False:
      return

  except SignupDisabledError:
    return frappe.throw("Signup is Disabled", "Sorry. Signup from Website is disabled.")

  if login:
    frappe.local.login_manager.user = user
    frappe.local.login_manager.post_login()
    if frappe.form_dict['use_jwt']:
      from renovation_core import on_session_creation
      on_session_creation(frappe.local.login_manager)

  # because of a GET request!
  frappe.db.commit()

  if not login:
    return frappe.get_doc("User", user)


def redirect_post_login(desk_user, redirect_to=None):
  # redirect!
  frappe.local.response["type"] = "redirect"

  if not redirect_to:
    # the #desktop is added to prevent a facebook redirect bug
    redirect_to = "/desk#desktop" if desk_user else "/me"

  frappe.local.response["location"] = redirect_to
