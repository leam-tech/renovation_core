import random

from six import string_types

import frappe
import jwt
from frappe import _
from frappe.auth import LoginManager
from frappe.utils import cint, get_url, get_datetime
from frappe.utils.password import check_password, passlibctx, update_password
from renovation_core.utils import update_http_response

from .sms_setting import send_sms


@frappe.whitelist(allow_guest=True)
def generate_otp(medium="sms", medium_id=None, sms_hash=None, purpose="login", lang="en"):
  """
  Generate and Send an OTP through the medium specified. we generate new pin on each call, ignoring previous pins

  3 variables available to render in template:
    - otp
    - mobile_no (if sms)
    - email (if email)
    - user (the User object)

  :param medium: 'email' or 'sms'
  :param medium_id: The actual email/mobile_no
  :param sms_hash: The hash that should be appended to OTP SMS
  :param purpose: Specify an optional purpose (login, pwd_reset) to make a custom context
  :param lang: Language of the OTP message (SMS or Email)
  """

  if medium not in ("sms", "email"):
    frappe.throw("medium can only be 'sms' or 'email'")

  if not medium_id:
    frappe.throw(f"medium_id is mandatory")

  user = get_linked_user(id_type=medium, id=medium_id)
  if user:
    lang = frappe.db.get_value("User", user, "language")
  frappe.local.lang = lang

  # generate a pin
  otp = frappe.safe_decode(str(get_otp()))

  # saving the hashed pin, not the pin as is
  hashed_pin = passlibctx.hash(otp)
  expires_in_sec = (cint(frappe.db.get_value(
      "System Settings", None, "verification_otp_validity")) or 15) * 60

  frappe.cache().set_value(
      get_otp_redis_key(
          medium, medium_id,
          purpose),
      hashed_pin,
      expires_in_sec=expires_in_sec
  )

  status = "success"
  if medium == "sms":
    sms_otp_template = frappe.db.get_value(
        "System Settings", None, "sms_otp_template")
    if not sms_otp_template:
      frappe.throw("Please set SMS OTP Template in System Settings")
    sms_otp_template = frappe.get_doc("SMS Template", sms_otp_template)
    render_params = frappe._dict(
        otp=otp,
        mobile_no=medium_id,
        user=frappe.get_doc("User", user) if user else frappe._dict()
    )
    msg = frappe.render_template(
        sms_otp_template.template, render_params)
    if sms_hash:
      msg = msg + u"\n" + sms_hash
    sms = send_sms([medium_id], msg, success_msg=False)
    status = "fail"
    # Since SMS Settings might remove or add '+' character, we will check against the last 5 digits
    if sms and isinstance(sms, list) and len(sms) == 1 and (medium_id[-5:] in sms[0] if isinstance(sms[0], string_types) else medium_id[-5:] in sms[0].sent_to):
      status = "success"
  elif medium == "email":
    email_otp_template = frappe.db.get_value(
        "System Settings", None, "email_otp_template")
    if not email_otp_template:
      frappe.throw("Please set Email OTP Template in System Settings")
    email_otp_template = frappe.get_doc("Email Template", email_otp_template)
    render_params = frappe._dict(
        otp=otp,
        email=medium_id,
        user=frappe.get_doc("User", user) if user else frappe._dict()
    )
    status = "fail"
    try:
      frappe.sendmail(
          recipients=[medium_id],
          delayed=False,
          subject=frappe.render_template(
              email_otp_template.subject, render_params),
          message=frappe.render_template(
              email_otp_template.response, render_params)
      )
      status = "success"
    except frappe.OutgoingEmailError:
      status = "fail"

  return frappe._dict({"status": status, medium: medium_id})


def generate_otp_deprecated():
  medium = frappe.local.form_dict.medium or "sms"
  mobile = frappe.local.form_dict.mobile
  email = frappe.local.form_dict.email
  sms_hash = frappe.local.form_dict.hash
  update_http_response(generate_otp(medium, mobile or email, sms_hash))


@frappe.whitelist(allow_guest=True)
def verify_otp(medium="sms", medium_id=None, otp=None, login_to_user=False, purpose="login"):
  """
  Verify the OTP against the previously generated OTP.
  :param medium: 'email' or 'sms'
  :param medium_id: The actual email/mobile_no
  :param otp: User input
  :param login_to_user: Check this flag to login to the associated user
  :param purpose: If purpose was specified while calling generate_otp, it is mandatory to use the same here
  """
  if medium not in ("sms", "email"):
    frappe.throw("medium can only be 'sms' or 'email'")

  if not medium_id:
    frappe.throw(f"medium_id is mandatory")

  def http_response(out):
    r = frappe._dict(status=out, medium=medium_id)
    return r

  user = None
  if login_to_user:
    user = get_linked_user(id_type=medium, id=medium_id)
    if not user:
      return http_response("no_linked_user")

  redis_key = get_otp_redis_key(medium, medium_id, purpose)
  hashed_otp = frappe.safe_decode(
      frappe.cache().get_value(redis_key, expires=True))

  if not hashed_otp:
    return http_response("no_otp_for_mobile")

  if not passlibctx.verify(otp, hashed_otp):
    return http_response("invalid_otp")

  if login_to_user == 1:
    l = LoginManager()
    l.login_as(user)
    l.resume = False
    l.run_trigger('on_session_creation')

  return http_response("verified")


def verify_otp_deprecated():
  medium = frappe.local.form_dict.medium or "sms"
  mobile = frappe.local.form_dict.mobile
  email = frappe.local.form_dict.email
  pin = frappe.local.form_dict.pin
  login = cint(frappe.local.form_dict.loginToUser or "0")

  r = verify_otp(medium=medium, medium_id=mobile or email,
                 otp=pin, login_to_user=login)
  # Response Compatibility
  if r.status == "no__for_mobile":
    r.status = "no_pin_for_mobile"
  elif r.status == "invalid_otp":
    r.status = "invalid_pin"
  update_http_response(r)


def get_otp_redis_key(medium, medium_id, purpose):
  return f"{purpose}_{medium}:{medium_id}"


def get_linked_user(id_type, id):
  """
  Returns the user associated with the details
  :param id_type: either 'mobile' or 'email'
  :param id: the email/mobile
  """
  if id_type not in ("mobile", "sms", "email"):
    frappe.throw(f"Invalid id_type: {id_type}")

  if id_type in ("mobile", "sms"):
    id_type = "mobile_no"

  return frappe.db.get_value("User", {id_type: id})


def get_otp(length=6):
  return random.sample(range(int('1' + '0' * (length - 1)), int('9' * length)), 1)[0]


@frappe.whitelist(allow_guest=True)
def pin_login(user, pin, device=None):
  """
  Login using the user's email and the quick login pin
  :param user: The active user
  :param pin: The quick login pin
  :param device: Clear all sessions of device
  """
  from frappe.sessions import clear_sessions
  login = LoginManager()

  if not frappe.cache().get_value(f'can_use_quick_login_pin', user=user, expires=True):
    login.fail('Quick Login PIN time expired', user=user)

  login.check_if_enabled(user)
  if not check_password(user, pin, doctype='User', fieldname='quick_login_pin'):
    login.fail('Incorrect password', user=user)

  login.login_as(user)
  login.resume = False
  login.run_trigger('on_session_creation')
  if device:
    clear_sessions(user, True, device)
  return frappe.session.user


@frappe.whitelist(allow_guest=True)
def get_token(user, pwd, expires_in=3600, expire_on=None, device=None):
  """
  Get the JWT Token
  :param user: The user in ctx
  :param pwd: Pwd to auth
  :param expires_in: number of seconds till expiry
  :param expire_on: yyyy-mm-dd HH:mm:ss to specify the expiry (deprecated)
  :param device: The device in ctx
  """
  if not frappe.db.exists("User", user):
    raise frappe.ValidationError(_("Invalide User"))

  from frappe.sessions import clear_sessions
  login = LoginManager()
  login.check_if_enabled(user)
  if not check_password(user, pwd):
    login.fail('Incorrect password', user=user)
  login.login_as(user)
  login.resume = False
  login.run_trigger('on_session_creation')

  _expires_in = 3600
  if cint(expires_in):
    _expires_in = cint(expires_in)
  elif expire_on:
    _expires_in = (get_datetime(expire_on) - get_datetime()).total_seconds()


  token = get_bearer_token(
    user=user,
    expires_in=_expires_in
  )
  frappe.local.response["token"] = token["access_token"]
  frappe.local.response.update(token)


def get_oath_client():
  client = frappe.db.get_value("OAuth Client", {})
  if not client:
    # Make one auto
    client = frappe.get_doc(frappe._dict(
        doctype="OAuth Client",
        app_name="default",
        scopes="all openid",
        redirect_urls=get_url(),
        default_redirect_uri=get_url(),
        grant_type="Implicit",
        response_type="Token"
    ))
    client.insert(ignore_permissions=True)
  else:
    client = frappe.get_doc("OAuth Client", client)

  return client


def get_bearer_token(user, expires_in=3600):
  import hashlib
  import jwt
  import frappe.oauth
  from oauthlib.oauth2.rfc6749.tokens import random_token_generator, OAuth2Token

  client = get_oath_client()
  token = frappe._dict({
      'access_token': random_token_generator(None),
      'expires_in': expires_in,
      'token_type': 'Bearer',
      'scopes': client.scopes,
      'refresh_token': random_token_generator(None)
  })
  bearer_token = frappe.new_doc("OAuth Bearer Token")
  bearer_token.client = client.name
  bearer_token.scopes = token['scopes']
  bearer_token.access_token = token['access_token']
  bearer_token.refresh_token = token.get('refresh_token')
  bearer_token.expires_in = token['expires_in'] or 3600
  bearer_token.user = user
  bearer_token.save(ignore_permissions=True)
  frappe.db.commit()

  # ID Token
  id_token_header = {
      "typ": "jwt",
      "alg": "HS256"
  }
  id_token = {
      "aud": "token_client",
      "exp": int((frappe.db.get_value("OAuth Bearer Token", token.access_token, "expiration_time") - frappe.utils.datetime.datetime(1970, 1, 1)).total_seconds()),
      "sub": frappe.db.get_value("User Social Login", {"parent": bearer_token.user, "provider": "frappe"}, "userid"),
      "iss": "frappe_server_url",
      "at_hash": frappe.oauth.calculate_at_hash(token.access_token, hashlib.sha256)
  }
  id_token_encoded = jwt.encode(
      id_token, "client_secret", algorithm='HS256', headers=id_token_header)
  id_token_encoded = frappe.safe_decode(id_token_encoded)
  token.id_token = id_token_encoded
  frappe.flags.jwt = id_token_encoded
  return token


@frappe.whitelist()
def get_jwt_token():
  """
  Get jwt token for the active user
  """
  return get_bearer_token(
      user=frappe.session.user, expires_in=86400
  )["access_token"]


@frappe.whitelist()
def change_password(old_password, new_password):
  """
  Update the password when old password is given
  :param old_password: The old password of the User
  :param new_password: The new password to set for the user
  """
  from frappe.core.doctype.user.user import test_password_strength, handle_password_test_fail

  check_password(user=frappe.session.user, pwd=old_password)

  user = frappe.get_doc("User", frappe.session.user)
  user_data = (user.first_name, user.middle_name,
               user.last_name, user.email, user.birth_date)
  result = test_password_strength(new_password, '', None, user_data)
  feedback = result.get("feedback", None)

  if feedback and not feedback.get('password_policy_validation_passed', False):
    handle_password_test_fail(result)

  update_password(user.name, new_password)
  return True
