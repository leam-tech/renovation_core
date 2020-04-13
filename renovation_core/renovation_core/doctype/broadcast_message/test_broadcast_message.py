# -*- coding: utf-8 -*-
# Copyright (c) 2020, LEAM Technology System and Contributors
# See license.txt
import frappe
from renovation_core.utils.generate_doc import generate_doc
from renovation_core.utils.test_runner import RenovationTestCase


class TestBroadcastMessage(RenovationTestCase):
  def test_check_exceptions(self):
    n = frappe.new_doc('Broadcast Message')
    n.update({
        "title": self.faker.sentence(),
        "body": self.faker.text(),
        "medium": "SMS",
        "targets": [
            {
                "type": "Mobile Nos",
                "mobile_nos": ''
            }
        ]
    })
    self.assertIs(n.send(), 'ok')

  def get_test_records(self):
    return generate_doc('Broadcast Message')
