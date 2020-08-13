import json

import frappe
import jwt
from frappe import _
from frappe.integrations.oauth2_logins import decoder_compat
from frappe.utils.oauth import get_oauth2_authorize_url, get_email, SignupDisabledError, get_oauth2_providers, \
  get_redirect_uri, get_first_name, get_last_name
from frappe.utils.password import get_decrypted_password
from six import string_types


@frappe.whitelist(allow_guest=True)
def get_oauth_url(provider: str, redirect_to: str) -> str:
  return get_oauth2_authorize_url(provider, redirect_to)


@frappe.whitelist(allow_guest=True)
def login_via_google(code, state=None, login=True, use_jwt=False):
  frappe.form_dict['use_jwt'] = use_jwt
  # In case the redirect should be to the frontend project, for instance.
  redirect_url = frappe.conf.get('google_redirect_url', None)

  return login_via_oauth2('google', code=code, state=state, decoder=decoder_compat, login=login,
                          redirect_url=redirect_url)


@frappe.whitelist(allow_guest=True)
def login_via_apple(code, state=None, login=True, use_jwt=False, option='native'):
  frappe.form_dict['use_jwt'] = use_jwt
  redirect_url = None
  if option == 'web':
    keys = frappe.conf.get('apple_login_web')
    redirect_url = keys.get('web_url')
  elif option == 'android':
    keys = frappe.conf.get('apple_login_android')
    redirect_url = keys.get('android_url')
  return login_via_oauth2_id_token('apple', code=code, state=state, login=login, decoder=decoder_compat,
                                   option=option, redirect_url=redirect_url)


@frappe.whitelist(allow_guest=True)
def redirect_apple_login_to_android(**kwargs):
  from urllib.parse import urlencode
  frappe.local.response["type"] = "redirect"
  frappe.local.response[
    "location"] = 'intent://callback?{args}/#Intent;package={android_package};scheme=signinwithapple;end'.format(
      args=urlencode(kwargs), android_package=frappe.conf.get('apple_login_android').get('android_package_id'))


def get_info_via_google(code):
  """
  # Sometimes we only need the id without logging in or creating a user.
  This function will return the details of google response (email, id, name, etc...)
  :param code: The auth code from Google's Auth server
  :return:
  """
  data = get_info_via_oauth("google", code, decoder=decoder_compat)
  if isinstance(data, string_types):
    data = json.loads(data)
  return data


def get_info_via_apple(code, option=None):
  """
  # Sometimes we only need the id without logging in or creating a user.
  This function will return the details of Apple's response (email, id, name, etc...)
  :param code: The auth code from Apple's Auth server
  :param option: The platform (native | web | android)
  :return:
  """

  redirect_url = None
  if option == 'web':
    keys = frappe.conf.get('apple_login_web')
    redirect_url = keys.get('web_url')
  elif option == 'android':
    keys = frappe.conf.get('apple_login_android')
    redirect_url = keys.get('android_url')

  data = get_info_via_oauth("apple", code, decoder=decoder_compat, id_token=True, option=option,
                            redirect_url=redirect_url)
  if isinstance(data, string_types):
    data = json.loads(data)
  return data


def login_via_oauth2(provider, code, state, decoder=None, login=True, redirect_url=None):
  info = get_info_via_oauth(provider, code, decoder, redirect_url=redirect_url)
  return login_oauth_user(info, provider=provider, state=state, login=login)


def login_via_oauth2_id_token(provider, code, state, decoder=None, login=True, option=None, redirect_url=None):
  info = get_info_via_oauth(provider, code, decoder, id_token=True, option=option, redirect_url=redirect_url)
  return login_oauth_user(info, provider=provider, state=state, login=login)


def login_oauth_user(data=None, provider=None, state=None, login=True):
  if isinstance(data, string_types):
    data = json.loads(data)

  user = get_email(data)

  if not user:
    frappe.throw(_("Please ensure that your profile has an email address"))

  try:
    user = update_oauth_user(user, data, provider)

  except SignupDisabledError:
    return frappe.throw("Signup is Disabled", "Sorry. Signup from Website is disabled.")

  if login:
    frappe.local.login_manager.user = user.name
    frappe.local.login_manager.post_login()
    if frappe.form_dict['use_jwt']:
      from renovation_core import on_session_creation
      on_session_creation(frappe.local.login_manager)

  # because of a GET request!
  frappe.db.commit()

  if not login:
    return user


def redirect_post_login(desk_user, redirect_to=None):
  # redirect!
  frappe.local.response["type"] = "redirect"

  if not redirect_to:
    # the #desktop is added to prevent a facebook redirect bug
    redirect_to = "/desk#desktop" if desk_user else "/me"

  frappe.local.response["location"] = redirect_to


def get_oauth2_flow(provider, option=None):
  from rauth import OAuth2Service

  # get client_id and client_secret
  params = get_oauth_keys(provider, option=option)

  oauth2_providers = get_oauth2_providers()

  # additional params for getting the flow
  params.update(oauth2_providers[provider]["flow_params"])

  # and we have setup the communication lines
  return OAuth2Service(**params)


def get_oauth_keys(provider, option=None):
  """get client_id and client_secret from database or conf"""

  key = "{provider}_login".format(provider=provider)
  if option:
    key = "{provider}_login_{option}".format(provider=provider, option=option)

    # try conf
  keys = frappe.conf.get(key)

  if not keys:
    # try database
    client_id, client_secret = frappe.get_value("Social Login Key", provider, ["client_id", "client_secret"])
    client_secret = get_decrypted_password("Social Login Key", provider, "client_secret")
    keys = {
        "client_id": client_id,
        "client_secret": client_secret

    }
    return keys
  else:
    return {
        "client_id": keys["client_id"],
        "client_secret": keys["client_secret"]
    }


def get_info_via_oauth(provider, code, decoder=None, id_token=False, option=None, redirect_url=None):
  flow = get_oauth2_flow(provider, option=option)
  oauth2_providers = get_oauth2_providers()

  args = {
      "data": {
          "code": code,
          "redirect_uri": get_redirect_uri(provider) if redirect_url is None else redirect_url,
          "grant_type": "authorization_code"
      }
  }

  if decoder:
    args["decoder"] = decoder

  session = flow.get_auth_session(**args)

  if id_token:
    parsed_access = json.loads(session.access_token_response.text)

    token = parsed_access['id_token']

    info = jwt.decode(token, flow.client_secret, verify=False)
  else:
    api_endpoint = oauth2_providers[provider].get("api_endpoint")
    api_endpoint_args = oauth2_providers[provider].get("api_endpoint_args")
    info = session.get(api_endpoint, params=api_endpoint_args).json()

  if not (info.get("email_verified") or info.get("email")):
    frappe.throw(_("Email not verified with {0}").format(provider.title()))

  return info


def update_oauth_user(user, data, provider):
  if isinstance(data.get("location"), dict):
    data["location"] = data.get("location").get("name")

  save = False

  if not frappe.db.exists("User", user) and not frappe.db.exists("User", {"username": user}) and not frappe.db.exists(
      "User", {"email": user}):

    # is signup disabled?
    if frappe.utils.cint(frappe.db.get_single_value("Website Settings", "disable_signup")):
      raise SignupDisabledError

    save = True
    user = frappe.new_doc("User")
    user.update({
        "doctype": "User",
        "first_name": get_first_name(data) or get_email(data),
        "last_name": get_last_name(data),
        "email": get_email(data),
        "gender": (data.get("gender") or "").title(),
        "enabled": 1,
        "new_password": frappe.generate_hash(get_email(data)),
        "location": data.get("location"),
        "user_type": "Website User",
        "user_image": data.get("picture") or data.get("avatar_url")
    })

  else:
    _user = None
    if frappe.db.exists("User", user):
      _user = frappe.get_doc("User", user)
    if not _user:
      users = frappe.get_all("User", filters={"username": user})
      if len(users):
        _user = frappe.get_doc("User", users[0].get('name'))
    if not _user:
      users = frappe.get_all("User", filters={"email": user})
      if len(users):
        _user = frappe.get_doc("User", users[0].get('name'))

    user = _user
    if not user.enabled:
      frappe.respond_as_web_page(_('Not Allowed'), _(
          'User {0} is disabled').format(user.email))
      return False

  if provider == "facebook" and not user.get_social_login_userid(provider):
    save = True
    user.set_social_login_userid(
        provider, userid=data["id"], username=data.get("username"))
    user.update({
        "user_image": "https://graph.facebook.com/{id}/picture".format(id=data["id"])
    })

  elif provider == "google" and not user.get_social_login_userid(provider):
    save = True
    user.set_social_login_userid(provider, userid=data["id"])

  elif provider == "github" and not user.get_social_login_userid(provider):
    save = True
    user.set_social_login_userid(
        provider, userid=data["id"], username=data.get("login"))

  elif provider == "frappe" and not user.get_social_login_userid(provider):
    save = True
    user.set_social_login_userid(provider, userid=data["sub"])

  elif provider == "office_365" and not user.get_social_login_userid(provider):
    save = True
    user.set_social_login_userid(provider, userid=data["sub"])

  elif provider == "salesforce" and not user.get_social_login_userid(provider):
    save = True
    user.set_social_login_userid(
        provider, userid="/".join(data["sub"].split("/")[-2:]))

  elif not user.get_social_login_userid(provider):
    save = True
    user_id_property = frappe.db.get_value(
        "Social Login Key", provider, "user_id_property") or "sub"
    user.set_social_login_userid(provider, userid=data[user_id_property])

  if save:
    user.flags.ignore_permissions = True
    user.flags.no_welcome_mail = True

    # set default signup role as per Portal Settings
    default_role = frappe.db.get_single_value(
        "Portal Settings", "default_role")
    if default_role:
      user.add_roles(default_role)

    user.save()
  return user
