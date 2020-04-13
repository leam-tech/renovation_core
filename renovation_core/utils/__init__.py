import frappe


def get_request_method():
  return frappe.local.request.method


"""
DEPRECATED
"""


def get_request_body(as_json=False):
  # TODO: Remove this function
  return frappe.local.form_dict


def get_request_path():
  """
  /api/renovation/
  request_parts:
          0. api
          1. method
          2. renovation
          3. [doc		|	config	| session	| get_meta]
          4. [DocType	|	] ('Renovation Report')
          5. [DocName	|	] ('R-00002')
  """
  return frappe.request.path


def update_http_response(dict):
  frappe.local.response.update(dict)
