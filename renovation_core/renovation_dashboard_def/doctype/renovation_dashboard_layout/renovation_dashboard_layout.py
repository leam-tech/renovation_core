# -*- coding: utf-8 -*-
# Copyright (c) 2019, LEAM Technology System and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe.model.document import Document
from frappe.utils import cint


class RenovationDashboardLayout(Document):

  def validate(self):
    self.validate_roles()

  def validate_roles(self):
    if not self.get("is_user_custom") and len(self.get("roles")) == 0:
      frappe.throw("Roles are mandatory if not custom to user")
    elif cint(self.get("is_user_custom", 0)) and not self.get("user", None):
      frappe.throw("User is mandatory if is custom to user")
