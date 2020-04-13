# -*- coding: utf-8 -*-
# Copyright (c) 2018, Leam Technology Systems and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe.model.document import Document


class RenovationDocDefaults(Document):

  supported_types = [
      'Data',
      'Currency',
      'Int',
      'Float',
      'Select',
      'Link',
      'Date',
      'Table'
  ]

  def valdiate(self):

    # remove unsupported columns
    self.validate_supported_fieldtypes()

  def validate_supported_fieldtypes(self):
    for field in self.fields:
      if field.fieldtype not in RenovationDocDefaults.supported_types:
        self.fields.remove(field)

  def fetch_fields(self, mandatory=0):
    if not self.dt:
      frappe.throw("Pls select a doctype first")

    if mandatory:
      filters = {'parent': self.dt, 'reqd': 1}
    else:
      filters = {'parent': self.dt}

    # docfields
    docfields = frappe.get_all('DocField', fields=[
                               "name", "fieldname", "label", "fieldtype", "options"], filters=filters)

    # custom fields
    docfields.extend(frappe.get_all('Custom Field', fields=[
                     "name", "fieldname", "label", "fieldtype", "options"], filters=filters))

    # clear existing rows
    self.fields = []

    for field in docfields:
      if field.fieldtype not in RenovationDocDefaults.supported_types:
        continue
      self.append('fields', {
          'docfield': field.name,
          'fieldname': field.fieldname,
          'label': field.label,
          'fieldtype': field.fieldtype,

          'link_doctype': field.options if field.fieldtype == "Link" else None
      })
    return True

  def fetch_mandatory_fields(self):
    self.fetch_fields(1)


def fieldname_query(doctype, txt, searchfield, start, page_len, filters):
  """
  Combined field query, from DocFields and CustomFields
  """

  supported_types = [
      "'" + x + "'" for x in RenovationDocDefaults.supported_types]

  return frappe.db.sql("""
		
		select name, label, fieldname, fieldtype from `tabDocField`
			where
				(label like %(txt)s
					or fieldname like %(txt)s)
				and parent=%(dt)s
		
		UNION
		
		select name, label, fieldname, fieldtype from `tabCustom Field`
			where
				(label like %(txt)s
					or fieldname like %(txt)s)
				and dt=%(dt)s
		
		limit %(start)s, %(page_len)s
	""", {
      'txt': "%%%s%%" % txt,
      'supported_types': ", ".join(supported_types),
      'dt': filters.get('dt'),
      'start': start,
      'page_len': page_len
  })


@frappe.whitelist()
def get_docfield_info(docfield_name):
  return frappe.db.get_value("DocField", docfield_name, ['fieldname', 'fieldtype', 'options', 'label'], as_dict=True)
