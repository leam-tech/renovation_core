# -*- coding: utf-8 -*-
# Copyright (c) 2018, Leam Technology Systems and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import ast

import frappe
from frappe.model.document import Document
from renovation_core.utils.meta import clear_meta_cache
from six import string_types


class RenovationDocField(Document):
  def validate(self):
    if not frappe.get_meta(self.p_doctype).has_field(self.fieldname):
      frappe.throw("Field '{}' not present in parent '{}' DocType".format(
          self.fieldname, self.p_doctype))

  def autoname(self):
    self.name = self.p_doctype + "-" + self.fieldname

  def on_update(self):
    clear_meta_cache(self.p_doctype)


def toggle_enabled(doctype, fieldname, enabled=0, user=None, role_profile=None, ignore_parent_update=False):
  value_changed = False
  # get doc
  existing = frappe.get_list("Renovation DocField", filters={
      "p_doctype": doctype,
      "fieldname": fieldname,
  })

  if existing:
    doc = frappe.get_doc("Renovation DocField", existing[0].name)
  else:
    doc = frappe.new_doc("Renovation DocField")
    doc.p_doctype = doctype
    doc.fieldname = fieldname
    doc.renovation_enabled = 0 if ignore_parent_update else enabled
    value_changed = True
  # User Enable/Disable
  if user:
    doc, value_changed = update_child_values(
        doc, 'users', 'user', user, enabled, value_changed)

  # Role Profile Enable/Disable
  if role_profile:
    doc, value_changed = update_child_values(
        doc, 'role_profiles', 'role_profile', role_profile, enabled, value_changed)

  # Global Enable/Disable
  if not ignore_parent_update and doc.renovation_enabled != enabled:
    doc.renovation_enabled = enabled
    value_changed = True
  if value_changed:
    doc.save()


def update_child_values(doc, chielfield, cfield, cfval, enabled, value_changed=False):
  cdocs = doc.as_dict().get(chielfield, [])
  got_cfield = False
  for cdoc in cdocs:
    if cdoc.get(cfield) == cfval:
      got_cfield = True
      if cdoc.enabled != enabled:
        value_changed = True
        cdoc.enabled = enabled
      break
  if not got_cfield:
    cdocs.append({
        cfield: cfval,
        "enabled": enabled
    })
    value_changed = True
  if value_changed:
    doc.set(chielfield, cdocs)
  return doc, value_changed


@frappe.whitelist()
def add_all_reqd_table_fields(doctypes=None):
  if not doctypes:
    doctypes = [x.name for x in frappe.get_all("DocType")]
  elif isinstance(doctypes, string_types):
    if doctypes.startswith('['):
      doctypes = ast.literal_eval(doctypes)
    else:
      doctypes = [doctypes]
  existing_fields = {}
  for f in frappe.get_all("Renovation DocField", fields=['fieldname', 'p_doctype']):
    if not existing_fields.get(f.p_doctype):
      existing_fields[f.p_doctype] = []
    existing_fields[f.p_doctype].append(f.fieldname)
  batch_size = 50
  for i in range(0, len(doctypes), batch_size):
    for doctype in doctypes[i:i + batch_size]:
      meta = frappe.get_meta(doctype)
      fields = [[f.fieldname, f.name]
                for f in meta.get("fields") if f.get('fieldname')]
      for field in fields:
        if field[0] in existing_fields.get(doctype, []):
          continue
        doc = frappe.new_doc('Renovation DocField')
        doc.update({
            "fieldname": field[0],
            "p_doctype": doctype,
            "reference_id": field[1]
        })
        doc.insert()
    frappe.db.commit()


@frappe.whitelist()
def get_fields_label(doctype):
  return [{"value": x.fieldname, "label": x.label or x.fieldname} for x in frappe.get_meta(doctype).fields if x.get('fieldname')]
