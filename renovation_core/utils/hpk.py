# -*- coding: utf-8 -*-
# Copyright (c) 2020, LEAM Technology System and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe.integrations.utils import make_post_request
from frappe.model.naming import make_autoname
from renovation_core.utils.fcm import make_communication_doc, \
  is_valid_session_id


def send_huawei_notification_to_topic(topic, title, body, data=None,
                                      custom_android_configuration=None):
  if not data:
    data = frappe._dict({})

  data.message_id = "HUAWEI-{}-{}".format(topic,
                                          make_autoname("hash",
                                                        "Communication"))
  # Message id response
  response = send_huawei_notifications(
    topic=topic, title=title, body=body, data=data,
    custom_android_configuration=custom_android_configuration)
  if response:
    make_communication_doc(data.message_id, title, body, data, topic=topic)


def send_huawei_notifications(tokens=None, topic=None, title=None, body=None,
                              data=None, custom_android_configuration=None):
  config = frappe.get_site_config().get("huawei_push_kit_config")
  if not config or not config.get('app_id') or not config.get(
    'client_id') or not config.get('client_secret'):
    frappe.log_error(
      title="Huawei Push Kit Error",
      message="Message: {}".format(frappe._("Missing secret keys in config")))
    return
  authorization_token = get_huawei_auth_token(config)
  if not authorization_token:
    frappe.log_error(
      title="Huawei Push Kit Error",
      message="Message: {}".format(frappe._("Authorization token missing.")))
    return
  url = "https://push-api.cloud.huawei.com/v1/{}/messages:send".format(
    config.get('app_id'))
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
  message = {
    "data": frappe.as_json(data) if data else {},
    "notification": {"title": title, "body": body},
    "android": {
      "notification": {
        "click_action": {
          "type": 3
        }
      }
    }
  }
  if custom_android_configuration and isinstance(custom_android_configuration,
                                                 dict):
    message['android'].update(custom_android_configuration)
  response = None
  headers = {"Content-Type": "application/json",
             "Authorization": authorization_token}
  if tokens and len(tokens):
    message.update({"token": tokens})
    try:
      payload = frappe._dict(validate_only=False, message=message)
      response = make_post_request(url, data=frappe.as_json(payload),
                                   headers=headers)
      huawei_push_kit_error_handler(tokens=tokens, topic=topic, title=title,
                                    body=body,
                                    data=data,
                                    recipient_count=len(tokens),
                                    request_params=message)
    except Exception as exc:
      huawei_push_kit_error_handler(tokens=tokens, topic=topic, title=title,
                                    body=body,
                                    data=data,
                                    exc=exc,
                                    recipient_count=len(tokens),
                                    request_params=message)
    print("Sending to tokens: {}".format(tokens))
  elif topic:
    message.update({"topic": topic})
    try:
      payload = frappe._dict(validate_only=False, message=message)
      response = make_post_request(url, data=frappe.as_json(payload),
                                   headers=headers)
      huawei_push_kit_error_handler(tokens=tokens, topic=topic, title=title,
                                    body=body,
                                    data=data,
                                    request_params=message)
    except Exception as exc:
      huawei_push_kit_error_handler(tokens=tokens, topic=topic, title=title,
                                    body=body,
                                    data=data,
                                    exc=exc,
                                    request_params=message)
    print("Sent TOPIC {} Msg: {}".format(topic, response))
  return response


def get_huawei_tokens_for(target, roles=None, users=None):
  if target == "Roles":
    users = [x.parent for x in frappe.db.get_all(
      "Has Role", fields=["distinct parent"],
      filters={"role": ["IN", roles or []]})]
    target = "Users"

  if target != "Users":
    frappe.throw("Invalid Target")

  tokens = []
  for u in users:
    tokens.extend(get_huawei_client_tokens(user=u))

  return [x for x in tokens if len(x) > 0]


def send_huawei_notification_to_user(user, title, body, data=None,
                                     custom_android_configuration=None):
  tokens = get_huawei_tokens_for("Users", users=[user])
  if not data:
    data = frappe._dict({})
  # for saving purpose
  data.message_id = "HUAWEI-{}-{}".format(user,
                                          make_autoname("hash",
                                                        "Communication"))
  # Batch Response
  response = send_huawei_notifications(
    tokens=tokens, title=title, body=body, data=data,
    custom_android_configuration=custom_android_configuration)
  if response:
    make_communication_doc(data.message_id, title, body, data, user=user)


def get_huawei_client_tokens(user=None):
  """
  Returns a list of valid user Huawei tokens
  """
  if not user:
    user = frappe.session.user if frappe.session else "Guest"
  tokens = []
  for t in frappe.get_all("Huawei User Token",
                          fields=["name", "token", "linked_sid"],
                          filters={"user": user}):
    if t.linked_sid and not is_valid_session_id(t.linked_sid):
      frappe.delete_doc("Huawei User Token", t.name, ignore_permissions=True)
      continue
    tokens.append(t.token)
  return tokens


def delete_huawei_invalid_tokens(tokens):
  for t in tokens:
    t = frappe.db.get_value("Huawei User Token", {"token": t})
    if t:
      frappe.delete_doc("Huawei User Token", t, ignore_permissions=True)


def get_huawei_auth_token(config):
  if not config or not config.get('app_id') or not config.get(
    'client_id') or not config.get('client_secret'):
    frappe.log_error(
      title="Huawei Push Kit Error",
      message="Message: {}".format(frappe._("Missing secret keys in config")))
    return
  cache_auth_token = check_redis_cache_for_huawei_auth_token()
  if cache_auth_token:
    return cache_auth_token
  url = "https://oauth-login.cloud.huawei.com/oauth2/v3/token"
  headers = {"Content-Type": "application/x-www-form-urlencoded",
             "Accept": "application/json"}
  payload = {
    "grant_type": "client_credentials",
    "client_id": config.get("client_id"),
    "client_secret": config.get("client_secret")
  }
  access_token = ''
  try:
    response = make_post_request(url, data=payload,
                                 headers=headers)
    access_token = "{} {}".format(response.get('token_type'),
                                  response.get('access_token'))
    set_redis_cache_huawei_auth_token(access_token, response.get('expires_in'))
  except Exception as exc:
    status_code = frappe.flags.integration_request.status_code
    error = frappe.parse_json(frappe.flags.integration_request.json())
    huawei_error_code = error.get('error')
    sub_error = error.get('sub_error')
    error_description = error.get('error_description')
    print(
      "{}\nStatus Code: {}\nHuawei Error: {}\nSub Error: {}\nError Description: {}".format(
        str(exc), status_code,
        huawei_error_code,
        sub_error,
        error_description))
    frappe.log_error(
      title="Huawei Push Kit Error",
      message="{}\n{}\nStatus Code: {}\nHuawei Error: {}\nSub Error: {}\nError Description: {}".format(
        "Get Authorization token error.",
        str(exc),
        status_code,
        huawei_error_code,
        sub_error,
        error_description))
  return access_token


def check_redis_cache_for_huawei_auth_token():
  user = get_default_values_for_redis_key().user
  key = get_default_values_for_redis_key().key
  val = frappe.cache().get_value(key, user=user, expires=True)
  return val


def get_default_values_for_redis_key():
  return frappe._dict(user='Administrator', key='huawei_auth_token')


def set_redis_cache_huawei_auth_token(auth_token: str, expires_in_sec):
  user = get_default_values_for_redis_key().user
  key = get_default_values_for_redis_key().key
  frappe.cache().set_value(key, auth_token, user=user,
                           expires_in_sec=expires_in_sec - 10)


def huawei_push_kit_error_handler(tokens=None, topic=None, title=None,
                                  exc=None, body=None, data=None,
                                  recipient_count=1, request_params=None):
  # {
  #   "code": "80000000",
  #   "msg": "Success",
  #   "requestId": "157440955549500001002006"
  # }
  status_code = frappe.flags.integration_request.status_code
  response = None
  try:
    response = frappe.parse_json(frappe.flags.integration_request.json())
  except Exception as e:
    pass
  huawei_error_code = response.get('error') if isinstance(response,
                                                          dict) else ''
  sub_error = response.get('sub_error') if isinstance(response, dict) else ''
  error_description = response.get('error_description') if isinstance(response,
                                                                      dict) else ''
  success_count = 0
  failure_count = 0
  if isinstance(response, dict) and response.get('code') == '80000000':
    success_count = recipient_count
  elif isinstance(response, dict) and response.get('code') == '80100000':
    msg = frappe.parse_json(response.get('msg'))
    success_count = msg.get('success', 0)
    failure_count = msg.get('failure', 0)
    delete_huawei_invalid_tokens(
      frappe.parse_json(msg.get("illegal_tokens", "")))
  preMessage = "Tokens: {}\nTopic: {}\nTitle: {}\nBody: {}\nData: {}\nSuccess/Recipients: {}/{} \nFailure:{}".format(
    tokens, topic, title, body, data, success_count, recipient_count,
    failure_count)
  if response and response.get('code') == '80000000':
    return
  code = response.get('code') if isinstance(response, dict) else ''
  message = response.get('msg') if isinstance(response, dict) else ''
  print(
    "- EXC\nCode: {}\nMessage: {}".format(code, message))
  frappe.log_error(
    title="Huawei Push Kit Error",
    message="{}\nEXC: {}\nCode: {}\nMessage: {}\nStatus Code: {}\nHuawei Error Code: {}\nSub Error: {}\nError Description: {}\n Request Params: {}".format(
      preMessage,
      str(exc),
      code,
      message,
      status_code,
      huawei_error_code,
      sub_error,
      error_description,
      request_params
    ))


def notify_via_hpk(title, body, data=None, roles=None, users=None, topics=None,
                   tokens=None, custom_android_configuration=None):
  frappe.enqueue("renovation_core.utils.hpk._notify_via_hpk",
                 enqueue_after_commit=True,
                 title=title, body=body, data=data, roles=roles, users=users,
                 topics=topics, tokens=tokens,
                 custom_android_configuration=custom_android_configuration)


def _notify_via_hpk(title, body, data=None, roles=None, users=None,
                    topics=None, tokens=None,
                    custom_android_configuration=None):
  users = set(users or [])
  if roles:
    users.union(set([x.parent for x in frappe.db.get_all("Has Role", fields=[
      "distinct parent"], filters={"role": ["IN", roles or []]})]))
  if data == None:
    data = frappe._dict()

  if not isinstance(data, dict):
    frappe.throw("Data should be a key-value pair for HPK")
  else:
    data = frappe._dict(data)

  for user in users:
    send_huawei_notification_to_user(user, title=title, body=body, data=data,
                                     custom_android_configuration=custom_android_configuration)

  topics = set(topics or [])
  for topic in topics:
    send_huawei_notification_to_topic(topic=topic, title=title, body=body,
                                      data=data,
                                      custom_android_configuration=custom_android_configuration)

  tokens = set(tokens or [])
  if len(tokens):
    send_huawei_notifications(list(tokens), title=title, body=body, data=data,
                              custom_android_configuration=custom_android_configuration)
