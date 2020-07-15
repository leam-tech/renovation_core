import base64
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
def login_via_google(code, state=None):
  return login_via_oauth2('google', code=code, state=state, decoder=decoder_compat)


def login_via_oauth2(provider, code, state, decoder=None):
  info = get_info_via_oauth(provider, code, decoder)
  return login_oauth_user(info, provider=provider, state=state)


def login_oauth_user(data=None, provider=None, state=None):
  if isinstance(data, string_types):
    data = json.loads(data)

  if isinstance(state, string_types):
    state = base64.b64decode(state)
    state = json.loads(state.decode("utf-8"))

  user = get_email(data)

  if not user:
    frappe.throw(_("Please ensure that your profile has an email address"))

  try:
    if update_oauth_user(user, data, provider) is False:
      return

  except SignupDisabledError:
    return frappe.throw("Signup is Disabled", "Sorry. Signup from Website is disabled.")

  frappe.local.login_manager.user = user
  frappe.local.login_manager.post_login()

  # because of a GET request!
  frappe.db.commit()

  if state:
    redirect_to = state.get("redirect_to", None)
    redirect_post_login(desk_user=frappe.local.response.get('message') == 'Logged In', redirect_to=redirect_to)


def redirect_post_login(desk_user, redirect_to=None):
  # redirect!
  frappe.local.response["type"] = "redirect"

  if not redirect_to:
    # the #desktop is added to prevent a facebook redirect bug
    redirect_to = "/desk#desktop" if desk_user else "/me"

  frappe.local.response["location"] = redirect_to
