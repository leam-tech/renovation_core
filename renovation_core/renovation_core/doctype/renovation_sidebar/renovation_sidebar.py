# -*- coding: utf-8 -*-
# Copyright (c) 2019, LEAM Technology System and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe.model.document import Document


class RenovationSidebar(Document):
  pass


def make_sample_sidebar():
  frappe.get_doc({
      "applicable_roles": [
          {
              "parent": "42fabc0073",
              "parentfield": "applicable_roles",
              "parenttype": "Renovation Sidebar",
              "role": "System Manager"
          }
      ],
      "docstatus": 0,
      "doctype": "Renovation Sidebar",
      "items": [
          {
              "is_group": 0,
              "nesting_level": 0,
              "parent": "42fabc0073",
              "parentfield": "items",
              "parenttype": "Renovation Sidebar",
              "target": "User",
              "target_type": "DocType",
              "title": "User",
          },
          {
              "is_group": 0,
              "nesting_level": 0,
              "parent": "42fabc0073",
              "parentfield": "items",
              "parenttype": "Renovation Sidebar",
              "target": "Broadcast Message",
              "target_type": "DocType",
              "title": "Broadcast Message",
          },
          {
              "is_group": 0,
              "nesting_level": 0,
              "parent": "42fabc0073",
              "parentfield": "items",
              "parenttype": "Renovation Sidebar",
              "target": "File",
              "target_type": "DocType",
              "title": "File",
          }
      ],
      "modified": "2020-04-12 23:09:49.703726",
      "name": "42fabc0073",
      "title": "General"
  }).insert()
