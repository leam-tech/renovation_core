# -*- coding: utf-8 -*-
# Copyright (c) 2019, Leam Technology Systems and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import os

import frappe
from frappe import scrub
from frappe.model.document import Document
from frappe.modules.utils import export_module_json


class RenovationDashboard(Document):
  def autoname(self):
    if not self.name:
      self.name = self.title

  def on_update(self):
    path = export_module_json(
        doc=self, is_standard=self.is_standard == "Yes", module=self.module
    )
    if path:
      # py
      if not os.path.exists(path + '.py'):
        with open(path + '.py', 'w') as f:
          f.write("""from __future__ import unicode_literals

import frappe


def get_context(**kwargs):
	# do your magic here
	pass
""")

  def get_chart_meta(self, **kwargs):
    m = {
        "name": self.name,
        "title": self.title,
        "enabled": self.enable,
        "is_standard": self.is_standard,
        "subtitle": self.subtitle or "",
        "type": self.type,
        "exc_type": self.exc_type,
        "params": [{
            "param": p.param,
            "label": p.label,
            "reqd": p.reqd,
            "options": p.options,
            "type": p.type,
            "default_value": p.default_value
        } for p in self.params]
    }
    if self.exc_type == "cmd":
      m['cmd'] = self.cmd
    elif self.exc_type == "eval":
      m['eval'] = self.eval_code
    return m

  def get_chart_data(self, **kwargs):
    return {
        "Meta": self.get_chart_meta(**kwargs),
        "Data": self.ready_chart_data(**kwargs)
    }

  def ready_chart_data(self, **kwargs):
    cmd = self.cmd
    if (self.exc_type == "cmd" and not cmd) or not self.eval_code:
      cmd = self.get_default_cmd()
    if self.exc_type == "eval" and self.eval_code:
      return eval(self.eval_code)
    else:
      if kwargs.get('cmd'):
        del kwargs['cmd']
      return self.call_cmd(cmd, **kwargs)

  def clear_cache_on_doc_events(self, doc, method):
    if self.exc_type != "cmd" or self.cmd or self.eval_code:
      return

    cmd = self.get_default_cmd(function="clear_cache_on_doc_events")
    try:
      return self.call_cmd(cmd, doc=doc, method=method)
    except AttributeError:
      pass

  def get_default_cmd(self, function="get_context"):
    cmd = os.path.join("{}.{}.{}.{}.{}".format(frappe.get_module_path(scrub(self.module)), scrub(self.doctype),
                                               scrub(self.name), scrub(self.name), function))
    cmd = '.'.join(cmd.split('/')[-2:])
    return cmd

  def call_cmd(self, cmd, **kwargs):
    dicts = self.as_dict()
    dicts.update(kwargs)
    return frappe.call(cmd or self.cmd, **dicts)
