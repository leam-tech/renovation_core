import random
import re

import frappe
from faker import Faker
from frappe.utils import cint, flt
from six import string_types

from .common_for_runner_and_generator import CommonForTestRunnerAndGenerator

"""
Generates JSON from templates
[
  "{{ repeat(5,7) }}"",
  {
    first_name: "{{ firstName() }}"
  }
]

Gives:
[
  { first_name: "Alice" },
  { first_name: "Bob" },
  { first_name: "John" },
  { first_name: "Billy" },
  { first_name: "Alice" },
]

Functions
- firstName()
- lastName()
- email()
- gender()
- city()
- state()
- country()
- lorem()
- integer(min, max)
- floating(min, max, precision)
- random()
::also allow kwargs in function args.
"""


def generate_json(template, faker_seed=None, faker_lang=None):
  return JSONGenerator(template, faker_seed=faker_seed, faker_lang=faker_lang).generate()


class JSONGenerator(CommonForTestRunnerAndGenerator):

  generated_values = frappe._dict()

  def __init__(self, template, faker_seed=None, faker_lang=None):
    super(JSONGenerator, self).__init__()
    if isinstance(template, string_types):
      template = frappe.parse_json(template)
    self.template = template
    self.faker = Faker(faker_lang)
    self.unique_values = frappe._dict()

  def generate(self):
    return self.get_template_value(self.template)

  def get_template_value(self, t):
    """
      ctx: Context for function types
    """
    if isinstance(t, dict):
      return self.get_dict_template_value(t)
    elif isinstance(t, (list, tuple)):
      return self.get_list_template_value(t)
    elif isinstance(t, string_types):
      return self.get_string_template_value(t)

    return t

  def get_list_template_value(self, t):
    if not t or not len(t):
      return t

    if re.search(r'\((.*[^)])\)', str(t[0])):
      reteat = re.findall(r'\((.*[^)])\)', str(t[0]))[0].split(',')
      return self.list_repeat(reteat, str(t[1]))
    return t

  def get_dict_template_value(self, t):
    if not isinstance(t, dict):
      return t

    # we have to execute function types at the very end
    # so we have to know if function types exists
    # https://stackoverflow.com/a/624939/2041598

    n = frappe._dict()
    fn_types = []
    for k, v in t.items():
      if hasattr(v, "__call__"):
        fn_types.append(k)
      else:
        n[k] = self.get_template_value(v)

    for k in fn_types:
      n[k] = t[k](n)

    return n

  def get_function_value(self, t, ctx):
    return t(ctx)

  def list_repeat(self, params, obj):
    params = [cint(x) for x in params]
    if len(params) == 1:
      n = params[0]
    else:
      n = self.faker.random_choices(elements=params, length=1)[0] or 1

    self.generated_values = frappe._dict()  # reset unique-randoms for lists
    return [self.get_template_value(obj) for i in range(n)]

  def firstName(self):
    return self.get_random_name()

  def lastName(self):
    return self.get_random_name()

  def get_random_name(self):
    return self.faker.name()

  def gender(self):
    return ["Male", "Female"][random.randint(0, 1)]

  def get_random_domain_name(self):
    return self.faker.domain_name()

  def lorem(self):
    return self.faker.paragraph()

  def integer(self, _min=0, _max=None, step=1):
    """
    integer(10) -----> [0,10]
    integer(5, 10) --> [5,10]
    """
    if _max == None:
      _max = _min
      _min = 0

    _min = cint(_min)
    _max = cint(_max)

    return self.faker.random_int(min=cint(_min), max=cint(_max), step=step)

  def floating(self, _min, _max=None, _precision=None):
    """
    Usage:
      {
        # price: 32.34
        price: r'{{ floating(20, 60, 2 )}}'
      }
    """
    _precision = _precision or 2
    if _max == None:
      _max = _min
      _min = 0

    _min = flt(_min)
    _max = flt(_max)

    return flt(random.uniform(_min, _max), precision=_precision)

  def random_select(self, *args):
    """
    Usage:
      {
        priority: r'{{ random("High", "Low", "Medium") }}'
      }
    """
    v = args[random.randint(0, len(args) - 1)]
    if isinstance(v, string_types) and v[0] in ('"', "'"):
      v = eval(v)
    return v
