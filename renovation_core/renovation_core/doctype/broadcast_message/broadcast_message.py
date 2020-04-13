# -*- coding: utf-8 -*-
# Copyright (c) 2020, LEAM Technology System and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe.model.document import Document


class BroadcastMessage(Document):
  def validate(self):
    if self.medium not in ("FCM", "SMS", "Email"):
      frappe.throw("Invalid Broadcast Medium")

    self.validate_targets()

  def validate_targets(self):
    for t in self.targets:
      if t.type == "DocType":
        if not t.target_dt or not t.user_path:
          frappe.throw(
              "Target DocType and User Path is mandatory for Target type DocType")
      elif t.type == "CMD" and not t.cmd:
        frappe.throw("CMD is mandatory")
      elif t.type == "FCM Topic" and not t.fcm_topic:
        frappe.throw("FCM Topic is mandatory")

  def send(self):

    t = frappe._dict(
        title=self.title,
        body=self.body,
        users=set(),
        fcm_tokens=set(),
        fcm_topics=set(),
        emails=set(),
        mobile_nos=set()
    )

    for target in self.targets:
      if target.type == "DocType":
        t.users.update(
            self.get_target_users_from_docs(
                target.target_dt, frappe.parse_json(target.filters),
                target.user_path
            )
        )

      elif target.type == "CMD":
        cmd_r = frappe.get_attr(target.cmd)()
        for p in ["users", "fcm_tokens", "fcm_topics", "emails", "mobile_nos"]:
          if p in cmd_r and isinstance(cmd_r[p], (list, tuple)):
            t[p].update(cmd_r[p])

      elif target.type == "FCM Topic":
        t.fcm_topics.add(target.fcm_topic)
      elif target.type == "Emails":
        t.emails.update(target.emails.split(","))
      elif target.type == "Mobile Nos":
        t.mobile_nos.update(target.mobile_nos.split(","))

    if self.medium == "FCM":
      self.send_via_fcm(t)
    elif self.medium == "SMS":
      self.send_via_mobile(t)
    elif self.medium == "Email":
      self.send_via_email(t)

    self.db_set("status", "Sent")
    self.reload()
    return "ok"

  def get_target_users_from_docs(self, doctype, filters, user_path):
    docs = frappe.get_list(doctype, filters=filters)

    def resolve_user(doc, path):
      field = path.pop(0)
      value = doc.get(field)

      if not value:
        print(
            "No value while resolving {} in {}:{}".format(
                field, doc.doctype, doc.name
            )
        )
        return None

      if not len(path):
        return value

      df = doc.meta.get_field(field)
      if df.fieldtype == "Link":
        return resolve_user(frappe.get_doc(df.options, value), path)
      elif df.fieldtype == "Dynamic Link":
        return resolve_user(frappe.get_doc(doc.get(df.options), value), path)
      else:
        return value

    users = []
    for d in docs:
      u = resolve_user(
          frappe.get_doc(doctype, d.name),
          user_path.split(".")[1:]
      )
      if u and frappe.db.exists("User", u):
        users.append(u)

    return users

  def send_via_fcm(self, t):
    from renovation_core.utils.fcm import notify_via_fcm
    notify_via_fcm(
        title=t.title,
        body=t.body,
        data=None,
        users=t.users,
        topics=t.fcm_topics,
        tokens=t.fcm_tokens
    )

  def send_via_mobile(self, t):
    from renovation_core.utils.sms_setting import send_sms
    user_mobiles = [
        x.mobile_no for x in frappe.get_all(
            "User",
            filters={"name": ["IN", t.users], "mobile_no": ["is", "set"]},
            fields=["mobile_no"]
        ) if x.mobile_no
    ]
    t.mobile_nos.update(user_mobiles)
    send_sms(
        receiver_list=list(t.mobile_nos),
        msg=t.body,
        sender_name='',
        success_msg=True
    )

  def send_via_email(self, t):
    frappe.throw("Not yet implemented")
