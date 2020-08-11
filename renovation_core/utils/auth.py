import random

import frappe
import jwt
from frappe import _
from frappe.auth import LoginManager
from frappe.utils import cint
from frappe.utils.password import check_password, passlibctx, update_password
from renovation_core.utils import update_http_response

from .sms_setting import send_sms


@frappe.whitelist(allow_guest=True)
def generate_otp(medium="sms", medium_id=None, sms_hash=None, purpose="login"):
  """
  Generate and Send an OTP through the medium specified. we generate new pin on each call, ignoring previous pins
  :param medium: 'email' or 'sms'
  :param medium_id: The actual email/mobile_no
  :param sms_hash: The hash that should be appended to OTP SMS
  :param purpose: Specify an optional purpose (login, pwd_reset) to make a custom context
  """

  if medium not in ("sms", "email"):
    frappe.throw("medium can only be 'sms' or 'email'")

  if not medium_id:
    frappe.throw(f"medium_id is mandatory")

  user = get_linked_user(id_type=medium, id=medium_id)

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
    msg = u"Your verification OTP is: " + otp
    if sms_hash:
      msg = msg + u". " + sms_hash
    sms = send_sms([medium_id], msg, success_msg=False)
    status = "fail"
    # Since SMS Settings might remove or add '+' character, we will check against the last 5 digits
    if sms and isinstance(sms, list) and len(sms) == 1 and medium_id[-5:] in sms[0]:
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
def get_token(user, pwd, expire_on=None, device=None):
  """
  Get the JWT Token
  :param user: The user in ctx
  :param pwd: Pwd to auth
  :param expire_on: yyyy-mm-dd HH:mm:ss to specify the expiry
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
  clear_sessions(user, True, device)
  if expire_on:
    frappe.flags.jwt_expire_on = expire_on


def make_jwt(user, expire_on=None, secret=None):
  if not frappe.session.get('sid') or frappe.session.sid == "Guest":
    return

  if frappe.session.user == frappe.session.sid:
    # active via apikeys/bearer tokens, no real session inplace
    from frappe.sessions import Session
    user_info = frappe.db.get_value(
        "User", frappe.session.user,
        ["user_type", "first_name", "last_name"], as_dict=1)
    frappe.local.session_obj = Session(
        user=frappe.session.user, resume=False,
        full_name=user_info.first_name, user_type=user_info.user_type)
    frappe.local.session = frappe.local.session_obj.data

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
  """
  Get jwt token for the active user
  """
  return make_jwt(user=frappe.session.user)


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
