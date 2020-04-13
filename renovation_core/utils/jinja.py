import re


def regex_replace(s, find, replace):
  """A non-optimal implementation of a regex filter"""
  return re.sub(find, replace, s)
