import unittest

import frappe
from faker import Faker
from frappe.model.delete_doc import delete_doc
from six import string_types

from .common_for_runner_and_generator import CommonForTestRunnerAndGenerator

"""
Docs:
- Every test_ methods in TestCases should be independent, so we create/destroy records in every setUp and tearDown
- Subclass RenovationTestCase instead of unittest.TestCase
- RenovationTestCase is written on the idea that every test_ methods are to be executed independently
  Therefore, we create and destroy fixtures in every setUp and tearDown
- get_test_records() method can be used to supply in the fixtures
- The fixtures support json-generated output. Relationships can be made by templating
  eg:

    full_name: { frappe.scrub(user_0.name) }
    --> full_name: johnny_depp
    # user_0 -- is the first user fixture made in the same testcase

"""


class RenovationTestCase(unittest.TestCase, CommonForTestRunnerAndGenerator):
  def __init__(self, methodName='runTest'):
    super(RenovationTestCase, self).__init__(methodName=methodName)
    self.faker = Faker()

  records_made = frappe._dict()

  def setUp(self):
    self.records_made = frappe._dict()
    self.unique_values = frappe._dict()
    self.set_up_test_records()

  def tearDown(self):
    self.remove_test_records()

  def set_up_test_records(self):
    frappe.db.commit()  # so we could rollback when any one of setting up fails
    to_make = self.get_test_records()
    self.records_made.fixture_creation_order = to_make.order
    try:
      for dt in to_make.order:
        _dt = frappe.scrub(dt)
        for d in to_make["records"][_dt]:
          if isinstance(d, string_types):
            d = frappe.parse_json(d)
          d["doctype"] = dt
          self.eval_record_exp(d)
          d = frappe.get_doc(d).insert()
          self.records_made.setdefault(_dt, []).append(d.as_dict())
    except Exception:
      frappe.db.rollback()
      print("\n\t[test_runner] Rollbacked created fixtures for this TestCase\n")
      print(frappe.get_traceback())

  def remove_test_records(self):
    for dt in reversed(self.records_made.fixture_creation_order):
      dt = frappe.scrub(dt)
      for doc in self.records_made[dt]:
        if not frappe.db.exists(doc.doctype, doc.name):
          continue
        if frappe.db.get_value(doc.doctype, doc.name, "docstatus") == 1:
          # submitted doc
          frappe.db.set_value(doc.doctype, doc.name, "docstatus", 2)
        delete_doc(doc.doctype, doc.name, ignore_permissions=True, force=True)

  def eval_record_exp(self, doc):
    if not doc or not hasattr(doc, "items"):
      return
    for a, b in doc.items():
      if isinstance(b, (list, tuple)):
        for c in b:
          self.eval_record_exp(c)
        continue
      if isinstance(b, string_types):
        for k, v in {"<%": "{%", "%>": '%}', '<<': r'{{', '>>': r'}}'}.items():
          b = b.replace(k, v)
        value = self.get_string_template_value(b, doc)
        doc[a] = value

  def get_test_records(self):
    """
    [Abstract]
    Should Return {
      order: ["DT 1", "DT 2"],
      records: {
        dt_1=[dict()],
        dt_2=[dict()]
      }
    }
    """
    return frappe._dict(
        order=[],
        records=[]
    )
