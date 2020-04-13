import unittest


class TestJinjaUtil(unittest.TestCase):
  def test_replace(self):
    from ..jinja import regex_replace
    t = regex_replace("HHH", "a", "b")
    self.assertEqual(t, "HHH")