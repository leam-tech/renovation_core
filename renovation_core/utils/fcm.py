import json

import firebase_admin
import frappe
from firebase_admin import credentials
from firebase_admin import messaging
from frappe.integrations.utils import make_post_request
from frappe.model.naming import make_autoname
from frappe.utils import cint, now
from six import string_types

"""
Targets
- All (including Guests)
- Roles
- User

Each FCM will call register_client on start, which will be stored in frappe.defaults
There is no expiry date for the tokens now
"""

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
def register_client(token, user=None, is_huawei_token=False):
  if not user:
    user = frappe.session.user if frappe.session else "Guest"

  if not isinstance(token, string_types):
    frappe.throw("Token should be a string")

  if len(token) < 10:
    frappe.throw("Invalid token")

  linked_sid = None
  # If current user is logged in with a normal frappe session that is valid,
  # Link the token to the sid
  if is_valid_session_id(frappe.session.sid):
    linked_sid = frappe.session.sid

  _add_user_token(user=user, token=token, linked_sid=linked_sid, is_huawei_token=is_huawei_token)
  return "OK"


def is_valid_session_id(sid):
  """
  Verifies if the sid is still a valid sid
  """
  from frappe.sessions import get_expiry_period_for_query
  device = frappe.db.sql(
      'SELECT `device` FROM `tabSessions` WHERE `sid`=%s', sid)
  device = device and device[0][0] or 'desktop'

  rec = frappe.db.sql("""
    SELECT `user`, `sessiondata`
    FROM `tabSessions` WHERE `sid`=%s AND
    (NOW() - lastupdate) < %s
    """, (sid, get_expiry_period_for_query(device)))

  return True if len(rec) else False


def get_client_tokens(user=None):
  """
  Returns a list of valid user fcm tokens
  """
  if not user:
    user = frappe.session.user if frappe.session else "Guest"

  tokens = []
  for t in frappe.get_all("FCM User Token", fields=["name", "token", "linked_sid"], filters={"user": user}):
    if t.linked_sid and not is_valid_session_id(t.linked_sid):
      frappe.delete_doc("FCM User Token", t.name, ignore_permissions=True)
      continue
    tokens.append(t.token)

  return tokens

def get_huawei_client_tokens(user=None):
  """
  Returns a list of valid user Huawei tokens
  """
  if not user:
    user = frappe.session.user if frappe.session else "Guest"

  tokens = []
  for t in frappe.get_all("Huawei User Token", fields=["name", "token", "linked_sid"], filters={"user": user}):
    if t.linked_sid and not is_valid_session_id(t.linked_sid):
      frappe.delete_doc("Huawei User Token", t.name, ignore_permissions=True)
      continue
    tokens.append(t.token)

  return tokens


def _add_user_token(user, token, linked_sid=None, is_huawei_token=False):
  dt = "FCM User Token"
  if is_huawei_token:
    dt = "Huawei User Token"
  _existing = frappe.db.get_value(
    dt,
    {"token": token},
    ["name", "user"],
    as_dict=1
  )
  if _existing:
    if _existing.user != user:
      frappe.delete_doc(dt, _existing.name, force=1, ignore_permissions=True)
    else:
      frappe.db.set_value(dt, _existing.name, "last_updated", now())
      return frappe.get_doc(dt, _existing.name)

  d = frappe.get_doc(frappe._dict(
      doctype=dt,
      user=user,
      token=token,
      linked_sid=linked_sid,
      last_updated=now()
  ))
  d.insert(ignore_permissions=True)
  return d



def _delete_user_token(user, token):
  ht = frappe.db.get_value("Huawei User Token", {"token": token, "user": user})
  if ht:
    frappe.delete_doc("Huawei User Token", ht, ignore_permissions=True)
  t = frappe.db.get_value("FCM User Token", {"token": token, "user": user})
  if not t:
    return

  frappe.delete_doc("FCM User Token", t, ignore_permissions=True)


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
    send_notification_to_user(user, title=title, body=body, data=data)

  topics = set(topics or [])
  for topic in topics:
    send_notification_to_topic(topic=topic, title=title, body=body, data=data)
    send_huawei_notification_to_topic(topic=topic, title=title, body=body, data=data)

  tokens = set(tokens or [])
  if len(tokens):
    send_fcm_notifications(list(tokens), title=title, body=body, data=data)
    send_huawei_notifications(list(tokens), title=title, body=body, data=data)



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

def send_huawei_notification_to_topic(topic, title, body, data=None):
  if not data:
    data = frappe._dict({})

  data.message_id = "HUAWEI-{}-{}".format(topic,
                                       make_autoname("hash", "Communication"))
  # Message id response
  response = send_huawei_notifications(
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

def _send_huawei_notification_to_user(user, title, body, data=None):
  tokens = get_huawei_tokens_for("Users", users=[user])

  if not data:
    data = frappe._dict({})
  # for saving purpose
  data.message_id = "HUAWEI-{}-{}".format(user,
                                       make_autoname("hash", "Communication"))

  # Batch Response
  response = send_huawei_notifications(
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
  if target == "Roles":
    users = [x.parent for x in frappe.db.get_all(
        "Has Role", fields=["distinct parent"], filters={"role": ["IN", roles or []]})]
    target = "Users"

  if target != "Users":
    frappe.throw("Invalid Target")

  tokens = []
  for u in users:
    tokens.extend(get_client_tokens(user=u))

  return [x for x in tokens if len(x) > 0]

def get_huawei_tokens_for(target, roles=None, users=None):
  if target == "Roles":
    users = [x.parent for x in frappe.db.get_all(
        "Has Role", fields=["distinct parent"], filters={"role": ["IN", roles or []]})]
    target = "Users"

  if target != "Users":
    frappe.throw("Invalid Target")

  tokens = []
  for u in users:
    tokens.extend(get_huawei_client_tokens(user=u))

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

def send_huawei_notifications(tokens=None, topic=None, title=None, body=None, data=None):
  app_id = frappe.get_site_config().get("app_id")
  if not app_id:
    frappe.log_error(
      title="Huawei Push Kit Error",
      message="Message: {}".format(frappe._("Missing app id in site config")))
    return
  url = "https://push-api.cloud.huawei.com/v1/{}/messages:send".format(app_id)
  # message format
  # {
  # data:str ,
  # notification: { 'title' , 'body' , 'image' },
  # android: check docs..,
  # apns: check docs..,
  # webpush: check docs..,
  # token: [] ,
  # topic: [] ,
  # condition : '' check docs...
  # }
  message={
    "data":frappe.as_json(data),
    "notification":{"title":title,"body":body},
    "token":tokens
  }
  response = None
  headers={"Content-Type": "application/json"}
  if tokens and len(tokens):
    try:
      payload = frappe._dict(validate_only=False, message=message)
      response = make_post_request(url, data=frappe.as_json(payload),
                               headers=headers)
      huawei_push_kit_error_handler(tokens=tokens, topic=topic, title=title, body=body,
                        data=data,
                        response=response,
                        recipient_count=len(tokens))
    except Exception as exc:
      huawei_push_kit_error_handler(tokens=tokens, topic=topic, title=title,
                                    body=body,
                                    data=data,
                                    response=exc,
                                    recipient_count=len(tokens))
    print("Sending to tokens: {}".format(tokens))
  elif topic:
    message.update({"topic":topic})
    try:
      payload = frappe._dict(validate_only=False, message=message)
      response = make_post_request(url, data=frappe.as_json(payload),
                               headers=headers)
      huawei_push_kit_error_handler(tokens=tokens, topic=topic, title=title, body=body,
                        data=data,
                        response=response,
                        recipient_count=len(tokens))
    except Exception:
      huawei_push_kit_error_handler(tokens=tokens, topic=topic, title=title,
                                    body=body,
                                    data=data,
                                    response=response,
                                    recipient_count=len(tokens))
    print("Sent TOPIC {} Msg: {}".format(topic, response))

  return response

def delete_huawei_invalid_tokens(tokens):
  for t in tokens:
    t = frappe.db.get_value("Huawei User Token", {"token": t})
    if t:
      frappe.delete_doc("Huawei User Token", t, ignore_permissions=True)


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
    t = frappe.db.get_value("FCM User Token", {"token": t})
    if t:
      frappe.delete_doc("FCM User Token", t, ignore_permissions=True)


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

def huawei_push_kit_error_handler(tokens=None, topic=None, title=None, body=None, data=None, response=None, recipient_count=1):
  # {
  #   "code": "80000000",
  #   "msg": "Success",
  #   "requestId": "157440955549500001002006"
  # }
  success_count=0
  failure_count=0
  if isinstance(response,dict) and response.get('code') == '80000000':
    success_count = recipient_count
  elif isinstance(response,dict) and response.get('code') == '80100000':
    msg = frappe.parse_json(response.get('msg'))
    success_count = msg.get('success')
    failure_count = msg.get('failure')
    delete_huawei_invalid_tokens(frappe.parse_json(msg.get("illegal_tokens","")))
  preMessage = "Tokens: {}\nTopic: {}\nTitle: {}\nBody: {}\nData: {}\n Success/Recipients: {}/{} \n Failure:{}".format(
    tokens, topic, title, body, data, success_count, recipient_count,failure_count)
  if response.get('code')=='80000000':
    return
  if isinstance(response,dict):
    code = response.get('code')
    message = response.get('msg')
    print(
      "- EXC\nCode: {}\nMessage: {}".format(code, message))
    frappe.log_error(
      title="Huawei Push Kit Error",
      message="{}\n- EXC\nCode: {}\nMessage: {}".format(preMessage,
                                                                    code,
                                                                    message
                                                                    ))
  else:
    exc = getattr(response, "exception", response)
    code = getattr(exc, "code", "no-code")
    message = getattr(exc, "message", exc)
    detail = getattr(exc, "detail", "no-details")
    print(
      "- EXC\nCode: {}\nMessage: {}\nDetail: {}".format(code, message, detail))
    frappe.log_error(
      title="Huawei Push Kit Error",
      message="{}\n- EXC\nCode: {}\nMessage: {}\nDetail: {}".format(preMessage,
                                                                    code,
                                                                    message,
                                                                    detail))


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
    frappe.db.set_value('Communication', {'name': (
        'in', [x.name for x in names])}, 'disable', 1, update_modified=False)
  return 'Success'


@frappe.whitelist()
def mark_notification_disable(message_id):
  return toggle_notification_disable(message_id, 1)


@frappe.whitelist()
def toggle_notification_disable(message_id, disable=1):
  frappe.db.set_value('Communication', {
                      "message_id": message_id}, 'disable', disable, update_modified=False)
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
    frappe.db.set_value('Communication', {'name': (
        'in', [x.name for x in names])}, 'seen', 1, update_modified=False)
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
  _delete_user_token(user=frappe.session.user, token=token)
