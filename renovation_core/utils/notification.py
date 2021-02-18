import ast
import json

import frappe
import six
from frappe import _
from frappe.email.doctype.notification.notification import get_context
from frappe.utils import strip_html_tags, strip_html

from .fcm import notify_via_fcm
from .sms_setting import get_sms_recipients_for_notification, send_sms

"""
Overrides
frappe.email.doctype.notification.send()
So that FCM can be a new channel
"""


def send_notification(self, doc):
  '''Build recipients and send Notification'''

  context = get_context(doc)
  context = {"doc": doc, "alert": self, "comments": None, "frappe": frappe}
  if doc.get("_comments"):
    context["comments"] = json.loads(doc.get("_comments"))

  if self.is_standard:
    self.load_standard_properties(context)

  if self.channel == 'Email':
    self.send_an_email(doc, context)
  elif self.channel == 'Slack':
    self.send_a_slack_msg(doc, context)
  elif self.channel == 'FCM':
    send_via_fcm(self, doc, context)
  elif self.channel == "SMS":
    recipients = get_sms_recipients_for_notification(
        notification=self, doc=doc, context=context)
    if recipients:
      send_sms(receiver_list=recipients, msg=strip_html(
          frappe.render_template(self.message, context)), provider=self.sms_providers)

  if self.set_property_after_alert:
    frappe.db.set_value(doc.doctype, doc.name, self.set_property_after_alert,
                        self.property_value, update_modified=False)
    doc.set(self.set_property_after_alert, self.property_value)


def send_via_fcm(notification, doc, context):
  title = notification.subject
  if "{" in title:
    title = frappe.render_template(notification.subject, context)

  body = strip_html_tags(frappe.render_template(notification.message, context))
  data = frappe.render_template(notification.fcm_data, context)
  custom_android_configuration = None
  if notification.get('custom_android_configuration') and notification.get('send_via_hcm'):
    custom_android_configuration = strip_html_tags(frappe.render_template(notification.get('custom_android_configuration'),context))


  # literal_eval supports dict parsing
  if data:
    try:
      data = ast.literal_eval(data)
    except Exception as e:
      frappe.log_error(message=frappe.get_traceback(), title=str(e))
      frappe.msgprint(
          "Error while parsing FCM Data in Notification: {}".format(notification.name))

  if not isinstance(data, dict):
    data = None

  recipients = get_fcm_recipients(notification, context)

  if recipients.users and len(recipients.users):
    for user in recipients.users:
      lang = frappe.get_cached_value('User', user, 'language')
      if isinstance(data, dict):
        data['lang'] = lang
      if isinstance(context, dict):
        context['lang'] = lang
      _body = body
      _title = title
      if notification and lang and frappe.get_cached_value('System Settings', 'System Settings', 'language') != lang:
        find_row = notification.get(
            'language_wise_content', {'language': lang})
        if find_row:
          if find_row[0].message:
            _body = strip_html_tags(
                frappe.render_template(find_row[0].message, context))
          if find_row[0].subject:
            _title = frappe.render_template(
                find_row[0].subject, context) if '{' in find_row[0].subject else find_row[0].subject
        else:
          _title = _(title, lang)
          _body = _(body, lang)
      notify_via_fcm(title=_title, body=_body, data=data, users=[user], send_via_hcm=notification.get('send_via_hcm') ,custom_android_configuration=custom_android_configuration)

  if recipients.topics and len(recipients.topics):
    notify_via_fcm(title=title, body=body, data=data, topics=recipients.topics, send_via_hcm=notification.get('send_via_hcm') ,custom_android_configuration=custom_android_configuration)

  if recipients.tokens and len(recipients.tokens):
    notify_via_fcm(title=title, body=body, data=data, tokens=recipients.tokens, send_via_hcm=notification.get('send_via_hcm') ,custom_android_configuration=custom_android_configuration)


def get_fcm_recipients(notification, context):
  users = []
  topics = []
  tokens = []
  if not notification or not notification.get("fcm_recipients"):
    return frappe._dict()

  for r in notification.get("fcm_recipients", []):
    target_type = r.get("target_type", None)
    target_user = r.get("target_user", None)
    target_role = r.get("target_role", None)

    if target_type == "User" and target_user:
      users.append(target_user)
    elif target_type == "Role" and target_role:
      users.extend([x.parent for x in frappe.get_all(
          "Has Role", ["parent"], {"parenttype": "User", "role": target_role})])
    elif target_type == "Role Profile":
      frappe.throw("Not implemented")
    elif target_type == "Topic" and r.get("topic", None):
      topics.append(r.get("topic"))
    elif target_type == "cmd":
      try:
        attr = frappe.get_attr(r.get("cmd"))
        param = r.get("cmd_param")
        if "{" in param:
          param = frappe.render_template(param, context)
        param = ast.literal_eval(param)

        u = attr(**param)
        if isinstance(u, six.string_types):
          users.append(u)
        elif isinstance(u, list):
          users.extend(u)
        elif isinstance(u, dict):
          tokens.extend(u.get("tokens", []))
          users.extend(u.get("users", []))
          topics.extend(u.get("topics", []))
        else:
          frappe.throw("FCM Recipient CMD should return either string or list")
      except Exception:
        frappe.log_error(title="FCM Recipients CMD Error",
                         message=frappe.get_traceback())
        frappe.msgprint("FCM Recipients CMD Error")

  return frappe._dict({
      "users": list(set(users)),
      "topics": topics,
      "tokens": tokens
  })
