import ast
import re

import frappe
from frappe import _
from frappe.model.base_document import _filter
from six import string_types


class CommonForTestRunnerAndGenerator():
  def __init__(self):
    self.unique_values = frappe._dict()
    self.records_made = frappe._dict()

  def get_filtered_single_data(self, key, filters, index_of=None, default=None):
    d = self.get_filtered_data(key, filters, default=default)
    if d and isinstance(d, (list, tuple)) and index_of is not None:
      try:
        return d[index_of]
      except KeyError:
        return d[0]
    return d or {}

  def get_filtered_data(self, key, filters, limit=None, default=None):
    if isinstance(filters, string_types):
      filters = frappe.parse_json(filters)
    try:
      return _filter(self.records_made[key], filters, limit=limit) or (ast.literal_eval(default) if isinstance(default, string_types) else default)
    except KeyError:
      return ast.literal_eval(default) if isinstance(default, string_types) else default

  def get_string_template_value(self, t, doc=None):
    value = None
    return_type = None
    if r"{{" in t or r'{%' in t:
      if self.__class__.__name__ == "JSONGenerator":
        context = {"doc": self}
      else:
        context = {"test_runner": self, "doc": doc}
      if t.startswith(r'[type::'):
        _type_end = re.search(r"\[type::.\S*]", t).end()
        return_type = t[7:_type_end-1]
        t = t[_type_end:]
      if t.startswith('[unique:'):
        x = re.findall(r"\[unique:.\S*]{", t)[0][1:-2].split(':')
        function_str = t[re.search(r"\[unique:.\S*]{", t).end()-1:]
        count_iter = 0
        while True:
          count_iter += 1
          v = frappe.render_template(function_str, context)
          if v and v not in self.unique_values.setdefault(x[1], []):
            value = v
            self.unique_values[x[1]].append(v)
            break
          if count_iter >= 100:
            print(_("Loops run 100 times for unique but not fund"))
            break
      else:
        value = frappe.render_template(t, context)
      if isinstance(value, string_types):
        try:
          if return_type:
            value = frappe.get_attr(return_type)(value)
          else:
            value = ast.literal_eval(value)
        except:
          pass
      t = value
    return t
