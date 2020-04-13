# -*- coding: utf-8 -*-
# Copyright (c) 2019, LEAM Technology System and Contributors
# See license.txt
from __future__ import unicode_literals

from renovation_core.utils.test_runner import RenovationTestCase


class TestRenovationSidebar(RenovationTestCase):
  pass
  # def setUp(self):
  # 	self.make_root_sidebar()
  # 	super(TestRenovationSidebar, self).setUp()

  # def test_record_exists_or_not(self):
  # 	records = self.records_made
  # 	print(records)

  # def make_root_sidebar(self):
  # 	if frappe.db.exists("Renovation Sidebar", {"renovation_sidebar_name": "All Menu"}):
  # 		return
  # 	d = frappe.new_doc("Renovation Sidebar")
  # 	d.update({
  # 		"renovation_sidebar_name": "All Menu",
  # 		"is_group": 1
  # 	})
  # 	d.save()

  # def get_test_records(self):
  # 	parent_menu_name = frappe.get_value("Renovation Sidebar", {"renovation_sidebar_name": "All Menu"}, as_dict=True)
  # 	print(parent_menu_name)
  # 	return frappe._dict(
  # 		order=['Renovation Sidebar'],
  # 		records=frappe._dict(
  # 			renovation_sidebar=generate_json([
  # 				r"{{ repeat(4) }}", frappe._dict(
  # 					renovation_sidebar_name= r"{{ doc.faker.sentence(nb_words=doc.faker.random_choices(elements=[1,3], length=1)[0]) }}",
  # 					doctype= "Renovation Sidebar",
  # 					is_group= r"{{ doc.faker.random_choices(elements=[1,0], length=1)[0] }}",
  # 					parent_renovation_sidebar= r'[unique:renovation_sidebar]<<test_runner.get_filtered_single_data("renovation_sidebar", {"is_group": 1}, test_runner.faker.random_choices(elements=[1,3], length=1)[0],"'+ cstr(parent_menu_name) +r'").get("name")>>'
  # 				)
  # 			])
  # 		)
  # 	)
