import unittest

import frappe
from frappe.utils import cint, flt
from six import string_types

from ..json_generator import generate_json



class TestJsonGenerator(unittest.TestCase):
  def test_fn_composing(self):
    # TODO: test using multiple combinations of these together
    t = generate_json(frappe._dict(a=r"{{ firstName() }} {{ integer(5, 10 )}}"))

    self.assertIsNotNone(t)

    a = t.get("a")
    self.assertIsInstance(a, string_types)
    self.assertIsInstance(cint(a.split(" ")[1]), int)

  def test_nesting_of_templates(self):
    # TODO: test child of child templating
    t = generate_json(
        frappe._dict(
            lvl1=frappe._dict(lvl2=frappe._dict(lvl3=r"{{ city() }}")),
            lvl1arr=[r"{{ repeat(3) }}",
                     frappe._dict(b=r"{{ city() }}")]
        )
    )

    self.assertIsNotNone(t)

    self.assertIsInstance(t.get("lvl1").get("lvl2").get("lvl3"), string_types)

    self.assertEqual(len(t.get("lvl1arr")), 3)
    self.assertIsInstance(t.get("lvl1arr")[0].get("b"), string_types)

  def test_repeat(self):
    t = generate_json([r"{{ repeat(4,10)}}", 3])
    self.assertGreaterEqual(len(t), 4)
    self.assertLessEqual(len(t), 10)
    self.assertEqual(t[0], 3)
    self.assertEqual(t[-1], 3)

    t = generate_json([r"{{repeat(4,10)}}", "ABC"])
    self.assertGreaterEqual(len(t), 4)
    self.assertLessEqual(len(t), 10)
    self.assertEqual(t[0], "ABC")
    self.assertEqual(t[-1], "ABC")

  def test_firstname(self):
    t = generate_json(frappe._dict(a=r"{{ firstName() }}"))
    self.assertIsNotNone(t)
    self.assertIsNotNone(t.get("a"))
    self.assertIsInstance(t.get("a"), string_types)
    self.assertGreater(len(t.get("a")), 0)

  def test_lastname(self):
    t = generate_json(frappe._dict(a=r"{{ lastName() }}"))
    self.assertIsNotNone(t)
    self.assertIsNotNone(t.get("a"))
    self.assertIsInstance(t.get("a"), string_types)
    self.assertGreater(len(t.get("a")), 0)

  def test_email(self):
    t = generate_json(frappe._dict(a=r"{{ email() }}"))
    self.assertIsNotNone(t)
    self.assertIsNotNone(t.get("a"))
    self.assertIsInstance(t.get("a"), string_types)
    self.assertGreater(len(t.get("a")), 0)
    self.assertIn("@", t.get("a"))

  def test_integer(self):
    from renovation_core.utils.debug import wait_for_attach
    wait_for_attach()
    t = generate_json(frappe._dict(a=r"{{ integer(10) }}"))
    self.assertIsNotNone(t)
    self.assertIsNotNone(t.get("a"))
    # type should be inteeger
    self.assertIsInstance(t.get("a"), int)
    self.assertGreaterEqual(t.get("a"), 0)
    self.assertLessEqual(t.get("a"), 10)

    # String when multiple numbers come together
    t = generate_json(
        frappe._dict(a=r"{{ integer(2, 10) }} {{ integer(50, 99) }}")
    )
    self.assertIsInstance(t.get("a"), string_types)
    v = [cint(x) for x in t.a.split(" ")]

    # [2,10]
    self.assertGreaterEqual(v[0], 2)
    self.assertLessEqual(v[0], 10)

    # [50,99]
    self.assertGreaterEqual(v[1], 50)
    self.assertLessEqual(v[1], 99)

  # floating

  def test_floating_basic(self):
    t = generate_json(frappe._dict(a=r"{{ floating(5) }}"))

    self.assertIsNotNone(t)
    n = t.get("a")
    self.assertIsNotNone(n)
    self.assertIsInstance(n, float)
    self.assertLessEqual(n, 5)

  def test_floating_precision(self):
    # t = generate_json(frappe._dict(a=r"{{ floating(5, 10, 3) }}"))
    # how do you test precision in py ? :P
    pass

  def test_floating_min_max(self):
    t = generate_json(frappe._dict(a=r"{{ floating(5, 10) }}"))
    self.assertIsNotNone(t)

    n = t.get("a")
    self.assertGreaterEqual(n, 5)
    self.assertLessEqual(n, 10)

  def test_floating_combined(self):
    t = generate_json(
        frappe._dict(a=r"{{ floating(70, 80) }} {{ floating(130, 150) }}")
    )
    self.assertIsNotNone(t)

    n = t.get("a")
    self.assertIsInstance(n, string_types)
    n_split = n.split(" ")
    self.assertEqual(len(n_split), 2)
    self.assertGreaterEqual(flt(n_split[0]), 70)
    self.assertGreaterEqual(flt(n_split[1]), 130)

  # lorem

  def test_lorem(self):
    t = generate_json(frappe._dict(a=r"{{ lorem() }}"))
    self.assertIsNotNone(t)

    s = t.get("a")
    self.assertIsInstance(s, string_types)

  def test_state(self):
    t = generate_json(frappe._dict(a=r"{{ state() }}"))
    self.assertIsNotNone(t)

    s = t.get("a")
    self.assertIsInstance(s, string_types)

  def test_country(self):
    t = generate_json(frappe._dict(a=r"{{ country() }}"))
    self.assertIsNotNone(t)

    s = t.get("a")
    self.assertIsInstance(s, string_types)

  def test_function(self):
    # just have to be a callable
    t = generate_json(frappe._dict(a=2, b=lambda obj: obj.a))
    self.assertIsNotNone(t)

    s = t.get("b")
    self.assertEqual(s, 2)

  def test_unique_firstName(self):
    t = generate_json(
        [r"{{ repeat(50) }}",
         frappe._dict(a=r"{{ unique-firstName() }}")]
    )
    self.assertIsNotNone(t)
    self.assertIsInstance(t, (list, tuple))

    names = set()
    for n in t:
      names.add(n.a)

    self.assertEqual(len(names), 50)

  def test_unique_integer(self):
    t = generate_json(
        [r"{{ repeat(50) }}",
         frappe._dict(a=r"{{ unique-integer(0, 100) }}")]
    )
    self.assertIsNotNone(t)
    self.assertIsInstance(t, (list, tuple))

    names = set()
    for n in t:
      names.add(n.a)

    self.assertEqual(len(names), 50)

  def test_random_select(self):
    t = generate_json([
      r"{{ repeat(5) }}",
      frappe._dict(a=r"{{ random_select('High', 'Medium', 'Low') }}")
    ])

    for n in t:
      self.assertIn(n.a, ["High", "Medium", "Low"])
