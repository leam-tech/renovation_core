import frappe
from .auth import generate_otp as _generate_otp, verify_otp as _verify_otp


@frappe.whitelist(allow_guest=True)
def get_reset_info(id_type, id):
  """
  Returns list of possible ways to reset the password, if any
  :param id_type: either 'mobile' or 'email'
  :param id: the email/mobile
  """
  user = get_user(id_type, id)
  if not user:
    return frappe._dict(has_medium=0)

  r = frappe._dict(
      has_medium=1,
      medium=[],
      hints=frappe._dict()
  )
  if user.mobile_no:
    r.medium.append("sms")
    r.hints["sms"] = user.mobile_no[-4:]

  if user.email:
    r.medium.append("email")
    r.hints["email"] = get_email_hint(user.email, 3)

  return r


@frappe.whitelist(allow_guest=True)
def generate_otp(id_type, id, medium, medium_id):
  """
  Sends an OTP via the medium specified
  :param id_type: either 'mobile' or 'email'
  :param id: the email/mobile
  :param medium: 'email' or 'sms'
  :param medium_id: The actual email/mobile_no
  """
  user = get_user(id_type, id)
  if not user:
    return frappe._dict(sent=0, reason="no-user")

  reset_info = get_reset_info(id_type, id)
  if medium not in reset_info.medium:
    return frappe._dict(sent=0, reason="invalid-medium")

  if not verify_medium_id(user, medium, medium_id):
    return frappe._dict(sent=0, reason="invalid-id")

  r = _generate_otp(medium=medium, medium_id=medium_id, purpose="pwd-reset")
  return frappe._dict(
    sent=1 if r.status == "success" else 0
  )

@frappe.whitelist(allow_guest=True)
def verify_otp(id_type, id, medium, medium_id, otp):
  """
  Verifies the otp sent, and returns a password reset token
  :param id_type: either 'mobile' or 'email'
  :param id: the email/mobile
  :param medium: 'email' or 'sms'
  :param medium_id: The actual email/mobile_no
  :param otp: The otp to verify
  """
  user = get_user(id_type, id)
  if not user:
    return frappe._dict(verified=0, reason="no-user")

  reset_info = get_reset_info(id_type, id)
  if medium not in reset_info.medium:
    return frappe._dict(verified=0, reason="invalid-medium")

  if not verify_medium_id(user, medium, medium_id):
    return frappe._dict(verified=0, reason="invalid-id")

  r = _verify_otp(medium=medium, medium_id=medium_id, otp=otp,
                  login_to_user=False, purpose="pwd-reset")

  if r.status != "verified":
    return frappe._dict(verified=0, reason=r.status)

  # generate reset token
  from frappe.utils import random_string
  token = random_string(32)
  user.db_set("reset_password_key", token)

  return frappe._dict(
    verified=1,
    reset_token=token
  )


@frappe.whitelist(allow_guest=True)
def update_password(reset_token, new_password):
  """
  Updates the user password
  :param reset_token: The token obtained while verifying otp
  :param new_password: The new password to be set for the user
  """
  from frappe.core.doctype.user.user import test_password_strength

  user = frappe.db.get_value("User", {"reset_password_key": reset_token})
  if not user:
    return frappe._dict(updated=0, reason="invalid-or-expired-key")
  
  user = frappe.get_doc("User", user)
  user_data = (user.first_name, user.middle_name,
               user.last_name, user.email, user.birth_date)
  result = test_password_strength(new_password, '', None, user_data)
  feedback = result.get("feedback", None)

  if feedback and not feedback.get('password_policy_validation_passed', False):
    return frappe._dict(
      updated=0, reason="weak-password"
    )

  from frappe.utils.password import update_password as _update_password
  _update_password(user.name, new_password)
  frappe.db.set_value("User", user.name, "reset_password_key", "")
  return frappe._dict(
    updated=1
  )


def get_user(id_type, id):
  """
  Returns the user associated with the details
  :param id_type: either 'mobile' or 'email'
  :param id: the email/mobile
  """
  if id_type not in ("mobile", "email"):
    frappe.throw("Invalid id_type")

  if id_type == "mobile":
    id_type = "mobile_no"

  user = frappe.db.get_value("User", {id_type: id})
  return frappe.get_doc("User", user) if user else None


def verify_medium_id(user, medium, medium_id):
  if medium == "sms":
    medium = "mobile_no"

  return user.get(medium) == medium_id


def get_email_hint(email, visible_count):
  import re
  email = email.split("@")
  _user = email[0]
  user_length = len(_user)
  if user_length > visible_count:
    cutoff_length = user_length - visible_count
    email[0] = re.sub(
        _user[-1 * cutoff_length:] + "$",
        cutoff_length * "*",
        _user
    )
  return "@".join(email)
