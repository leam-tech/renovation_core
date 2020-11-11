# -*- coding: utf-8 -*-
# Copyright (c) 2020, LEAM Technology System and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document


class SMSProvider(Document):
  def on_update(self):
    self.check_and_update_system_setting()

  def check_and_update_system_setting(self):
    if not frappe.db.get_default("sms_settings"):
      sys_setting = frappe.get_single("System Settings")
      sys_setting.set("sms_settings", self.name)
      sys_setting.flags.ignore_permissions = True
      sys_setting.save()
