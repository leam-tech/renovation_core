import random

import frappe
import jwt
from frappe import _
from frappe.auth import LoginManager
from frappe.utils import cint
from frappe.utils.password import check_password, passlibctx
from renovation_core.utils import update_http_response

from .sms_setting import send_sms


def generate_sms_pin():
  # we generate new pin on each call, ignoring previous pins
  mobile = frappe.local.form_dict.mobile

  # If mobile needs to automatically the received
  hash = frappe.local.form_dict.hash

  if not mobile:
    frappe.throw("No Mobile Number")

  user = get_linked_user(mobile)

  # generate a pin
  pin = frappe.safe_decode(str(get_pin()))

  # saving the hashed pin, not the pin as is
  hashed_pin = passlibctx.hash(pin)
  expires_in_sec = (cint(frappe.db.get_value(
      "System Settings", None, "verification_otp_validity")) or 15) * 60
  if user:
    frappe.cache().set_value(
        f"sms_user:{user}:{mobile}", hashed_pin, expires_in_sec=expires_in_sec)
  else:
    frappe.cache().set_value(f"sms:{mobile}",
                             hashed_pin, expires_in_sec=expires_in_sec)

  msg = u"Your verification OTP is: " + pin
  if hash:
    msg = msg + u". " + hash
  sms = send_sms([mobile], msg, success_msg=False)
  status = "fail"
  # Since SMS Settings might remove or add '+' character, we will check against the last 5 digits
  if sms and isinstance(sms, list) and len(sms) == 1 and mobile[-5:] in sms[0]:
    status = "success"
  update_http_response({"status": status, "mobile": mobile})


def verify_sms_pin():
  mobile = frappe.local.form_dict.mobile
  pin = frappe.local.form_dict.pin
  login = cint(frappe.local.form_dict.loginToUser or "0")

  if not mobile:
    frappe.throw("No Mobile Number")

  def http_response(out):
    update_http_response({"status": out, "mobile": mobile})

  user = None
  if login:
    user = get_linked_user(mobile)
    if not user:
      return http_response("no_linked_user")

  redis_key = f"sms_user:{user}:{mobile}" if login else f"sms:{mobile}"
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


def get_linked_user(mobile_no):
  return frappe.db.get_value("User", filters={"mobile_no": mobile_no})


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
