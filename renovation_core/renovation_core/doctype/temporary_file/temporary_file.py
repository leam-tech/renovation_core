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
    """
    Validate if a File document actually exists with the specified URL
    """
    if not frappe.db.get_value("File", {"file_url": self.file}):
      frappe.throw("No file exists with url {}".format(self.file))

  def validate_target_docname(self):
    """
    Validate if a document with specified name exists in the DocType
    """
    if not self.target_docname:
      return

    if not frappe.db.exists(self.target_doctype, self.target_docname):
      frappe.throw("Document {}: {} doesnt exist".format(
          self.target_doctype, self.target_docname))

  def validate_target_fieldname(self):
    """
    Validate if the fieldname specified is actually an Attach/Attach Image field in the target_doctype
    """
    if not self.target_fieldname:
      frappe.throw("Target DF is mandatory")
    m = frappe.get_meta(self.target_doctype)
    df = m.get_field(self.target_fieldname)
    if not df:
      frappe.throw("Fieldname {} doesnt exist in doctype {}".format(
          self.target_fieldname, self.target_doctype))

    if df.fieldtype not in ("Attach", "Attach Image"):
      frappe.throw("{} is not an attachment field".format(df.fieldname))	
