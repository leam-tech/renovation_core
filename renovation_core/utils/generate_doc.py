import copy

import frappe
from faker import Faker
from frappe.model import (table_fields, data_fieldtypes, no_value_fields, display_fieldtypes, optional_fields,
                          default_fields, numeric_fieldtypes, core_doctypes_list)
from frappe.utils import cstr
from renovation_core.utils.json_generator import generate_json

_Faker = Faker()
_ignore_fields_type = set(
    default_fields+optional_fields+no_value_fields+display_fieldtypes)
_ignore_fields_type.difference_update(set(table_fields))


def generate_doc(doctype):
  d = GenerateDoc(doctype)
  return d.get_data()


class GenerateDoc():
  def __init__(self, doctype, data=None):
    self.doctype = doctype
    self.meta = frappe.get_meta(self.doctype)
    self.record_field = frappe.scrub(self.doctype)
    self.data_serial = frappe._dict(doctype=self.doctype)
    self.get_ignore_doctypes_list()
    if data:
      self.data = data
      if not self.meta.istable:
        self.data.order.insert(0, doctype)
    else:
      self.data = frappe._dict(
          order=[doctype],
          records=frappe._dict()
      )
    self.render_fields()
    if not self.meta.istable:
      self.data.records[self.record_field] = self.get_generated_data()

  def get_generated_data(self):
    return generate_json([r'repeat(doc.faker.random_int(1,2))', self.data_serial])

  def get_data(self):
    return self.data

  def get_ignore_doctypes_list(self):
    self.ignore_doctypes_list = set(core_doctypes_list)
    if 'User' in self.ignore_doctypes_list:
      self.ignore_doctypes_list.remove('User')

  def render_fields(self):
    for f in self.meta.fields:
      if f.fieldtype in _ignore_fields_type:
        continue
      self.render_field(f)

  def render_field(self, f):
    if f.fieldtype in numeric_fieldtypes:
      self.render_numeric_fieldtypes_field(f)
    elif f.fieldtype in data_fieldtypes:
      self.render_data_fieldtypes_field(f)
    elif f.fieldtype in table_fields:
      if not f.options in self.data.order:
        i = GenerateDoc(f.options, self.data)
        self.data_serial[f.fieldname] = i.get_generated_data()

  def render_numeric_fieldtypes_field(self, field):
    if field.fieldtype == 'Int':
      self.data_serial[field.fieldname] = r'{{ doc.faker.random_int() }}'
    elif field.fieldtype in ('Float', 'Currency'):
      self.data_serial[field.fieldname] = r'{{ doc.faker.random_number() }}'
    elif field.fieldtype == 'Check':
      self.data_serial[field.fieldname] = r'{{ doc.faker.random_int(0,1) }}'
    elif field.fieldtype == 'Long Int':
      self.data_serial[field.fieldname] = r'{{ doc.faker.random_int(9999, 999999) }}'

  def render_data_fieldtypes_field(self, field):
    if field.fieldtype == 'Data':
      self.render_data_field(field)
    elif field.fieldtype == 'Link':
      self.render_link_filed(field)
    elif field.fieldtype == 'Dynamic Link':
      self.render_dynamic_field(field)
    elif field.fieldtype == 'Select':
      self.render_select_field(field)
    elif field.fieldtype in ('Date', 'Datetime'):
      self.render_date_field(field)
    elif field.fieldtype == 'Time':
      self.data_serial[field.fieldname] = r'{{ doc.faker.time() }}'
    elif field.fieldtype == 'Time':
      self.data_serial[field.fieldname] = r'{{ doc.faker.time() }}'
    elif field.fieldtype == 'Percent':
      self.data_serial[field.fieldname] = r'{{ doc.faker.randomize_nb_elements(max=100) }}'
    elif field.fieldtype == 'Small Text':
      self.data_serial[field.fieldname] = r'{{ doc.faker.paragraph() }}'
    elif field.fieldtype == 'Long Text':
      self.data_serial[field.fieldname] = r'{{ doc.faker.paragraphs()|join("\n") }}'
    elif field.fieldtype == 'Text Editor':
      self.data_serial[field.fieldname] = r'{{ doc.faker.paragraphs()|join("\n") }}'
    elif field.fieldtype == 'HTML Editor':
      self.data_serial[field.fieldname] = r'{{ doc.faker.paragraphs()|join("\n") }}'
    elif field.fieldtype == 'Markdown Editor':
      self.data_serial[field.fieldname] = r'{{ doc.faker.paragraphs()|join("\n") }}'
    elif field.fieldtype == 'Rating':
      self.data_serial[field.fieldname] = r'{{ doc.faker.random_int(1,5) }}'
    elif field.fieldtype == 'Color':
      self.data_serial[field.fieldname] = r'{{ doc.faker.color() }}'
    elif field.fieldtype == 'Barcode':
      self.data_serial[field.fieldname] = r'{{ doc.faker.ean() }}'
    elif field.fieldtype == 'Code':
      self.data_serial[field.fieldname] = r'{{ doc.faker.pystruct() }}'

  def render_data_field(self, field):
    if 'Email' in cstr(field.options) or 'email' in field.fieldname or 'mail' in field.fieldname:
      v = r'{{ doc.faker.email() }}'
    elif 'Phone' in cstr(field.options) or 'phone' in field.fieldname or 'mobile' in field.fieldname:
      v = r'{{ doc.faker.msisdn() }}'
    elif 'user_name' in field.fieldname:
      v = r'{{ doc.faker.user_name() }}'
    elif 'slug' in field.fieldname:
      v = r'{{ doc.faker.slug() }}'
    elif 'name' in field.fieldname:
      v = r'{{ doc.faker.name() }}'
    else:
      v = r'{{ doc.faker.text(140) }}'
    self.data_serial[field.fieldname] = v

  def render_date_field(self, field):
    if 'birth' in field.fieldname:
      v = r'{{ doc.faker.date_of_birth(minimum_age=18) }}'
    elif 'join' in field.fieldname:
      v = r'{{ doc.faker.date_time_between() }}'
    elif 'posting' in field.fieldname or 'transaction' in field.fieldname or 'order' in field.fieldname:
      v = r'{{ doc.faker.date_time_between("-2m") }}'
    elif 'due' in field.fieldname or 'schedule' in field.fieldname or 'appointment' in field.fieldname:
      v = r'{{ doc.faker.date_time_between("+1m") }}'
    else:
      v = r'{{ doc.faker.date_time_this_month() }}'
    self.data_serial[field.fieldname] = v

  def render_select_field(self, field):
    elements = cstr(field.options).split('\n')
    if elements:
      self.data_serial[field.fieldname] = r'{{ doc.faker.random_choices(' + cstr(
          elements) + r', 1)[0] }}'
    else:
      self.data_serial[field.fieldname] = r'{{ doc.faker.word() }}'

  def render_dynamic_field(self, field):
    if not hasattr(self.data_serial, field.options):
      self.render_field(self.meta.get_field(field.options))
    _f = copy.deepcopy(field)
    _f.options = self.data_serial[field.options]
    self.render_link_filed(_f)

  def render_link_filed(self, field):
    if field.fieldname == 'amended_from':
      return
    elif field.options == "DocType":
      self.get_ignore_doctypes_list()
      self.ignore_doctypes_list.add(field.options)
      d = frappe.get_all(field.options, [['name', 'not in', self.ignore_doctypes_list], [
                         'istable', '=', 0], ['issingle', '=', 0]], page_length=10)
      self.data_serial[field.fieldname] = _Faker.random_choices(
          [x.name for x in d], length=1)[0]
    else:
      self.data_serial[field.fieldname] = r'<<test_runner.get_filtered_single_data("' + frappe.scrub(
          field.options) + r'", {}, test_runner.faker.random_choices(elements=[1,3], length=1)[0]).get("name")>>'
      if not field.options in self.data.order:
        GenerateDoc(field.options, self.data)

  def check_field_for_dynami_link(self, field):
    return self.meta.get('fields', {'fieldtype': 'Dynamic Link', 'options': field.fieldname}) and True or False
