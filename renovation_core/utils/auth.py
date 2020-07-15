import random

import frappe
import jwt
from frappe import _
from frappe.auth import LoginManager
from frappe.utils import cint
from frappe.utils.password import check_password, passlibctx
from renovation_core.utils import update_http_response

from .sms_setting import send_sms


@frappe.whitelist(allow_guest=True)
def generate_otp():
  # we generate new pin on each call, ignoring previous pins
  medium = frappe.local.form_dict.medium or "sms"
  mobile = frappe.local.form_dict.mobile
  email = frappe.local.form_dict.email

  # If mobile needs to automatically the received
  hash = frappe.local.form_dict.hash

  if medium not in ("sms", "email"):
    frappe.throw("medium can only be 'sms' or 'email'")

  if medium == "sms" and not mobile:
    frappe.throw("No Mobile Number")
  elif medium == "email" and not email:
    frappe.throw("No email address")

  user = get_linked_user(mobile_no=mobile, email=email)

  # generate a pin
  pin = frappe.safe_decode(str(get_pin()))

  # saving the hashed pin, not the pin as is
  hashed_pin = passlibctx.hash(pin)
  expires_in_sec = (cint(frappe.db.get_value(
      "System Settings", None, "verification_otp_validity")) or 15) * 60
  if user:
    frappe.cache().set_value(
        f"{medium}_user:{user}:{mobile if medium=='sms' else email}", hashed_pin, expires_in_sec=expires_in_sec)
  else:
    frappe.cache().set_value(f"{medium}:{mobile if medium=='sms' else email}",
                             hashed_pin, expires_in_sec=expires_in_sec)

  status = "no-op"
  if medium == "sms":
    msg = u"Your verification OTP is: " + pin
    if hash:
      msg = msg + u". " + hash
    sms = send_sms([mobile], msg, success_msg=False)
    status = "fail"
    # Since SMS Settings might remove or add '+' character, we will check against the last 5 digits
    if sms and isinstance(sms, list) and len(sms) == 1 and mobile[-5:] in sms[0]:
      status = "success"
  elif medium == "email":
    email_otp_template = frappe.db.get_value(
        "System Settings", None, "email_otp_template")
    if not email_otp_template:
      frappe.throw("Please set Email OTP Template in System Settings")
    email_otp_template = frappe.get_doc("Email Template", email_otp_template)
    render_params = frappe._dict(
        otp=pin,
        email=email,
        user=frappe.get_doc("User", user) if user else frappe._dict()
    )
    status = "fail"
    try:
      frappe.sendmail(
          recipients=[email],
          subject=frappe.render_template(
              email_otp_template.subject, render_params),
          message=frappe.render_template(
              email_otp_template.response, render_params)
      )
      status = "success"
    except frappe.OutgoingEmailError:
      status = "fail"

  update_http_response(
      {"status": status, medium: mobile if medium == "sms" else email})


@frappe.whitelist(allow_guest=True)
def verify_otp():
  medium = frappe.local.form_dict.medium or "sms"
  mobile = frappe.local.form_dict.mobile
  email = frappe.local.form_dict.email

  if medium not in ("sms", "email"):
    frappe.throw("medium can only be 'sms' or 'email'")

  if medium == "sms" and not mobile:
    frappe.throw("No Mobile Number")
  elif medium == "email" and not email:
    frappe.throw("No email address")

  pin = frappe.local.form_dict.pin
  login = cint(frappe.local.form_dict.loginToUser or "0")

  def http_response(out):
    update_http_response(
        {"status": out, medium: mobile if medium == "sms" else email})

  user = None
  if login:
    user = get_linked_user(mobile_no=mobile, email=email)
    if not user:
      return http_response("no_linked_user")

  redis_key = f"{medium}_user:{user}:{mobile if medium=='sms' else email}" if login else f"{medium}:{mobile if medium=='sms' else email}"
  hashed_pin = frappe.safe_decode(
      frappe.cache().get_value(redis_key, expires=True))

  if not hashed_pin:
    return http_response("no_pin_for_mobile")

  if not passlibctx.verify(pin, hashed_pin):
    return http_response("invalid_pin")

  if login == 1:
    l = LoginManager()
    l.login_as(user)
    l.resume = False
    l.run_trigger('on_session_creation')

  return http_response("verified")


def get_linked_user(mobile_no, email):
  if mobile_no:
    return frappe.db.get_value("User", filters={"mobile_no": mobile_no})
  elif email:
    return frappe.db.get_value("User", filters={"email": email})


def get_pin(length=6):
  return random.sample(range(int('1' + '0' * (length - 1)), int('9' * length)), 1)[0]


@frappe.whitelist(allow_guest=True)
def pin_login(user, pin, device=None):
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
def get_token(user, pwd, expire_on=None, device=None):
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
  clear_sessions(user, True, device)
  if expire_on:
    frappe.flags.jwt_expire_on = expire_on


def make_jwt(user, expire_on=None, secret=None):
  if not frappe.session.get('sid') or frappe.session.sid == "Guest":
    return
  if not secret:
    secret = frappe.utils.password.get_encryption_key()
  if expire_on and not isinstance(expire_on, frappe.utils.datetime.datetime):
    expire_on = frappe.utils.get_datetime(expire_on)

  id_token_header = {
      "typ": "jwt",
      "alg": "HS256"
  }
  id_token = {
      "sub": user,
      "ip": frappe.local.request_ip,
      "sid": frappe.session.get('sid')
  }
  if expire_on:
    id_token['exp'] = int(
        (expire_on - frappe.utils.datetime.datetime(1970, 1, 1)).total_seconds())
  token_encoded = jwt.encode(
      id_token, secret, algorithm='HS256', headers=id_token_header).decode("ascii")
  frappe.flags.jwt = token_encoded
  return token_encoded


@frappe.whitelist()
def get_jwt_token():
  return make_jwt(user=frappe.session.user)
