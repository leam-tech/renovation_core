import json

import firebase_admin
import frappe
from firebase_admin import credentials
from firebase_admin import messaging
from frappe.model.naming import make_autoname
from frappe.utils import cint
from six import string_types

"""
Targets
- All (including Guests)
- Roles
- User

Each FCM will call register_client on start, which will be stored in frappe.defaults
There is no expiry date for the tokens now
"""

fcm_defaults_key = "fcm_reg_tokens"
firebase_app = None


def get_firebase_certificate():
  import os
  cred = frappe.get_site_config().get("firebase_service_account", None)
  if not cred and os.path.isfile("firebase-adminsdk-cred.json"):
    cred = "firebase-adminsdk-cred.json"

  if not cred:
    frappe.throw("Please define firebase_service_account in site_config")

  return credentials.Certificate(cred)


@frappe.whitelist(allow_guest=True)
def register_client(token, user=None):
  if not user:
    user = frappe.session.user if frappe.session else "Guest"

  if not isinstance(token, string_types):
    frappe.throw("Token should be a string")

  if len(token) < 10:
    frappe.throw("Invalid token")

  tokens = get_client_tokens(user)
  if token not in tokens:
    tokens.append(token)
    set_client_tokens(user, tokens)

  return "OK"


def get_client_tokens(user=None):
  if not user:
    user = frappe.session.user if frappe.session else "Guest"
  return json.loads(frappe.defaults.get_user_default(fcm_defaults_key, user) or "[]")


def set_client_tokens(user=None, tokens=[]):
  if not user:
    user = frappe.session.user if frappe.session else "Guest"
  frappe.defaults.set_user_default(fcm_defaults_key, json.dumps(tokens), user)


def notify_via_fcm(title, body, data=None, roles=None, users=None, topics=None, tokens=None):
  frappe.enqueue("renovation_core.utils.fcm._notify_via_fcm", enqueue_after_commit=True,
                 title=title, body=body, data=data, roles=roles, users=users, topics=topics, tokens=tokens)


def _notify_via_fcm(title, body, data=None, roles=None, users=None, topics=None, tokens=None):

  users = set(users or [])
  if roles:
    users.union(set([x.parent for x in frappe.db.get_all("Has Role", fields=[
                "distinct parent"], filters={"role": ["IN", roles or []]})]))

  if data == None:
    data = frappe._dict()

  if not isinstance(data, dict):
    frappe.throw("Data should be a key-value pair for FCM")
  else:
    data = frappe._dict(data)

  for user in users:
    send_notification_to_user(user, title=title, body=body, data=data)

  topics = set(topics or [])
  for topic in topics:
    send_notification_to_topic(topic=topic, title=title, body=body, data=data)

  tokens = set(tokens or [])
  if len(tokens):
    send_fcm_notifications(list(tokens), title=title, body=body, data=data)


def send_notification_to_topic(topic, title, body, data=None):
  if not data:
    data = frappe._dict({})

  data.message_id = "FCM-{}-{}".format(topic,
                                       make_autoname("hash", "Communication"))
  # Message id response
  response = send_fcm_notifications(
      topic=topic, title=title, body=body, data=data)
  if response:
    make_communication_doc(data.message_id, title, body, data, topic=topic)


def send_notification_to_user(user, title, body, data=None):
  tokens = get_tokens_for("Users", users=[user])

  if not data:
    data = frappe._dict({})
  # for saving purpose
  data.message_id = "FCM-{}-{}".format(user,
                                       make_autoname("hash", "Communication"))

  # Batch Response
  response = send_fcm_notifications(
      tokens=tokens, title=title, body=body, data=data)
  if response and response.success_count > 0:
    make_communication_doc(data.message_id, title, body, data, user=user)


def make_communication_doc(message_id, title, body, data, user=None, topic=None):
  notification_str = json.dumps({
      "title": title or "",
      "body": body or "",
      "data": data or {}
  })

  doc = frappe.get_doc({
      "message_id": data.message_id,
      "subject": "FCM {} {}".format(user or topic, title or ""),
      "doctype": "Communication",
      "communication_medium": "FCM",
      "sent_or_received": "Sent",
      "content": "Title: {}<br/>Body: {}<br/>Data: {}".format(title, body, json.dumps(data)),
      "text_content": notification_str,
      "user": user
  })
  doc.insert(ignore_permissions=True)


def get_tokens_for(target, roles=None, users=None):
  filters = {
      "defKey": fcm_defaults_key
  }
  if target == "Roles":
    users = [x.parent for x in frappe.db.get_all(
        "Has Role", fields=["distinct parent"], filters={"role": ["IN", roles or []]})]
    target = "Users"

  if target == "Users":
    filters["parent"] = ["IN", users or []]

  tokens = []
  for token_json in frappe.db.get_all("DefaultValue", fields=["parent", "defValue"], filters=filters):
    try:
      user_tokens = json.loads(token_json.defValue or "[]")
      for t in user_tokens:
        frappe.cache().set_value("fcm_{}".format(t), token_json.parent, expires_in_sec=20)
      tokens.extend(user_tokens)
    except:
      pass
  return [x for x in tokens if len(x) > 0]


def send_fcm_notifications(tokens=None, topic=None, title=None, body=None, data=None):
  global firebase_app
  if not firebase_app:
    firebase_app = firebase_admin.initialize_app(get_firebase_certificate())

  noti = messaging.Notification(title=title, body=body)
  response = None
  if tokens and len(tokens):
    print("Sending to tokens: {}".format(tokens))
    multicast_msg = messaging.MulticastMessage(
        tokens=tokens, notification=noti, data=data)
    # send_multicast returns a BatchResponse
    # https://firebase.google.com/docs/reference/admin/python/firebase_admin.messaging#firebase_admin.messaging.BatchResponse
    response = messaging.send_multicast(
        multicast_message=multicast_msg, app=firebase_app)
    print("FCM Response: Success: {} Failed: {} ".format(
        response.success_count, response.failure_count))
    fcm_error_handler(tokens=tokens, topic=topic, title=title, body=body, data=data,
                      responses=response.responses, recipient_count=len(tokens), success_count=response.success_count)
    delete_invalid_tokens(tokens, response.responses)
  elif topic:
    message = messaging.Message(topic=topic, notification=noti, data=data)
    response = messaging.send_all(messages=[message], app=firebase_app)
    print("Sent TOPIC {} Msg: {}".format(topic, response))
    fcm_error_handler(tokens=tokens, topic=topic, title=title, body=body, data=data,
                      responses=response.responses, recipient_count=1, success_count=0)

  return response


def delete_invalid_tokens(tokens, responses):
  """
  Responses dont give a hint of what token was used
  And we arent guaranteed if input token list and responses list match one to one
  """
  if len(tokens) != len(responses):
    return

  err_tokens = []
  i = 0
  for i in range(len(responses)):
    r = responses[i]
    if r.success:
      continue

    exc = getattr(r, "exception")
    if not exc:
      continue

    code = getattr(exc, "code")
    if not code or code not in ["registration-token-not-registered"]:
      continue

    err_tokens.append(tokens[i])

  # now lets dry run and confirm exceptions
  global firebase_app
  if not firebase_app:
    firebase_app = firebase_admin.initialize_app(get_firebase_certificate())
  noti = messaging.Notification(title="Test", body="Test")

  i = len(err_tokens) - 1
  while i >= 0:
    t = err_tokens[i]
    msg = messaging.Message(notification=noti, token=t)
    try:
      # dry run!
      r = messaging.send(msg, dry_run=True, app=firebase_app)
      err_tokens.pop(i)
    except:
      pass
    i -= 1

  # now all tokens in err tokens are problematic
  user_token = frappe._dict()
  for t in err_tokens:
    # we had 10 second buffer in redis while retrieving the tokens
    user = frappe.cache().get_value("fcm_{}".format(t))
    if not user:
      continue

    ts = user_token.setdefault(user, set())
    ts.add(t)

  for user in list(user_token.keys()):
    t = set(get_client_tokens(user) or [])
    new_tokens = list(t - user_token.get(user))
    print("Updated tokens: {}".format(", ".join(new_tokens)))
    set_client_tokens(user=user, tokens=new_tokens)
    frappe.log_error(
        title="Deleting FCM tokens for {}".format(user),
        message="The following tokens have been deleted: \n{}".format(
            "\n".join(list(user_token.get(user))))
    )


def fcm_error_handler(tokens=None, topic=None, title=None, body=None, data=None, responses=[], recipient_count=1, success_count=0):
  preMessage = "Tokens: {}\nTopic: {}\nTitle: {}\nBody: {}\nData: {}\n Success/Recipients: {}/{}".format(
      tokens, topic, title, body, data, success_count, recipient_count)
  for r in responses:
    if getattr(r, "success", False):
      continue

    exc = getattr(r, "exception", r)
    code = getattr(exc, "code", "no-code")
    message = getattr(exc, "message", exc)
    detail = getattr(exc, "detail", "no-details")
    print("- EXC\nCode: {}\nMessage: {}\nDetail: {}".format(code, message, detail))
    frappe.log_error(
        title="FCM Error", message="{}\n- EXC\nCode: {}\nMessage: {}\nDetail: {}".format(preMessage, code, message, detail))


@frappe.whitelist(allow_guest=True)
def get_user_notifications(limit_start=0, limit_page_length=20, _user=None, just_unseen=None, filters=None):
  user = _user or frappe.session.user

  _filters = filters or frappe._dict()

  _filters.update({
      "communication_medium": "FCM",
      "user": user,
      'ifnull(disable, 0)': 0
  })
  if not just_unseen is None:
    _filters["seen"] = cint(just_unseen)

  communications = frappe.get_all("Communication",
                                  fields=["message_id", "text_content",
                                          "seen", "communication_date"],
                                  filters=_filters,
                                  order_by="communication_date desc",
                                  limit_start=limit_start,
                                  limit_page_length=limit_page_length
                                  )

  ret = []
  for comm in communications:
    data = frappe._dict(json.loads(comm.text_content))
    data.message_id = comm.message_id
    data.seen = comm.seen
    data.communication_date = comm.communication_date
    ret.append(data)

  return ret


@frappe.whitelist()
def mark_all_as_disable(_user=None, filters=None):
  user = _user or frappe.session.user

  _filters = filters or frappe._dict()

  _filters.update({
      "communication_medium": "FCM",
      "user": user,
      "ifnull(disable, 0)": 0
  })
  names = frappe.get_all('Communication', _filters)
  if names:
    frappe.db.set_value('Communication', {'name': ('in', [x.name for x in names])}, 'disable', 1, update_modified=False)
  return 'Success'


@frappe.whitelist()
def mark_notification_disable(message_id):
  return toggle_notification_disble(message_id, 1)


@frappe.whitelist()
def toggle_notification_disble(message_id, disable=1):
  frappe.db.set_value('Communication', {"message_id": message_id}, 'disable', disable, update_modified=False)
  return 'Success'


@frappe.whitelist()
def mark_all_as_read(_user=None, filters=None):
  user = _user or frappe.session.user

  _filters = filters or frappe._dict()

  _filters.update({
      "communication_medium": "FCM",
      "user": user,
      "seen": 0
  })
  names = frappe.get_all('Communication', _filters)
  if names:
    frappe.db.set_value('Communication', {'name': ('in', [x.name for x in names])}, 'seen', 1, update_modified=False)
  return 'Success'


@frappe.whitelist()
def mark_notification_seen(message_id, seen=True):
  if seen:
    seen = 1
  else:
    seen = 0

  comm = frappe.db.get_value("Communication", fieldname="name", filters={
                             "message_id": message_id})
  frappe.db.set_value("Communication", comm, "seen", seen)
  return "OK"


def delete_token_on_logout():
  if not frappe.local.form_dict.fcm_token:
    return

  token = frappe.local.form_dict.fcm_token
  tokens = get_client_tokens()
  if not token in tokens:
    return

  tokens.remove(token)
  set_client_tokens(tokens=tokens)
