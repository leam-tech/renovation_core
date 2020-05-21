# -*- coding: utf-8 -*-
# Copyright (c) 2020, LEAM Technology System and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document


class TemporaryFile(Document):
  def validate(self):
    self.validate_file_url()
    self.validate_target_docname()
    self.validate_target_fieldname()

  def validate_file_url(self):
    if not frappe.db.get_value("File", {"file_url": self.file}):
      frappe.throw("No file exists with url {}".format(self.file))

  def validate_target_docname(self):
    if not self.target_dn:
      return

    if not frappe.db.exists(self.target_dt, self.target_dn):
      frappe.throw("Document {}: {} doesnt exist".format(
          self.target_dt, self.target_dn))

  def validate_target_fieldname(self):
    if not self.target_df:
      frappe.throw("Target DF is mandatory")
    m = frappe.get_meta(self.target_dt)
    df = m.get_field(self.target_df)
    if not df:
      frappe.throw("Fieldname {} doesnt exist in doctype {}".format(
          self.target_df, self.target_dt))

    if df.fieldtype not in ("Attach", "Attach Image"):
      frappe.throw("{} is not an attachment field".format(df.fieldname))	
