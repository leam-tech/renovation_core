import re

import frappe
from frappe import throw, _, msgprint
from frappe.core.doctype.sms_settings.sms_settings import get_headers, create_sms_log
from six import string_types


def validate_receiver_nos(receiver_list):
  plus = frappe.db.get_value('SMS Settings', None, 'start_with_plus')
  validated_receiver_list = []
  for d in receiver_list:
    # remove invalid character
    for x in [' ', '-', '(', ')']:
      d = d.replace(x, '')
    if plus and plus == "Add" and d[0] != '+':
      d = '+'+d
    elif plus and plus == "Remove" and d[0] == '+':
      d = d[1:]
    validated_receiver_list.append(d)

  if not validated_receiver_list:
    throw(_("Please enter valid mobile nos"))
  return validated_receiver_list


@frappe.whitelist()
def send_sms(receiver_list, msg, sender_name='', success_msg=True):

  import json
  if isinstance(receiver_list, string_types):
    receiver_list = json.loads(receiver_list)
    if not isinstance(receiver_list, list):
      receiver_list = [receiver_list]

  receiver_list = validate_receiver_nos(receiver_list)

  arg = {
      'receiver_list': receiver_list,
      'message'		: frappe.safe_decode(msg).encode('utf-8'),
      'success_msg'	: success_msg
  }

  if frappe.db.get_value('SMS Settings', None, 'sms_gateway_url'):
    return send_via_gateway(arg)
  else:
    msgprint(_("Please Update SMS Settings"))
    return "Fail"


def send_via_gateway(arg):
  ss = frappe.get_doc('SMS Settings', 'SMS Settings')
  headers = get_headers(ss)

  args = {ss.message_parameter: re.sub(
      r'\s+', ' ', safe_decode(arg.get('message')))}
  for d in ss.get("parameters"):
    if not d.header:
      args[d.parameter] = d.value

  success_list = []
  for d in arg.get('receiver_list'):
    args[ss.receiver_parameter] = d
  url = ss.sms_gateway_url
  if "%(" in url:
    url = ss.sms_gateway_url % args
  status = send_request(url, {} if "%(" in ss.sms_gateway_url else args,
                        headers, ss.use_post, ss.get('request_as_json'))
  if 200 <= status < 300:
    success_list.append(d)

  if len(success_list) > 0:
    args.update(arg)
    if frappe.db.exists("DocType", "SMS Log"):
      create_sms_log(args, success_list)
    if arg.get('success_msg'):
      frappe.msgprint(_("SMS sent to following numbers: {0}").format(
          "\n" + "\n".join(success_list)))
  return success_list


def send_request(gateway_url, params, headers=None, use_post=False, request_as_json=False):
  import requests

  if not headers:
    headers = get_headers()
  if use_post:
    if request_as_json:
      response = requests.post(gateway_url, headers=headers, json=params)
    else:
      response = requests.post(gateway_url, headers=headers, data=params)
  else:
    response = requests.get(gateway_url, headers=headers, params=params)
  response.raise_for_status()
  return response.status_code


def safe_decode(string, encoding='utf-8'):
  try:
    string = string.decode(encoding)
  except Exception:
    pass
  return string
