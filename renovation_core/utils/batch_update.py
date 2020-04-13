from __future__ import unicode_literals

import json

import frappe
from frappe import _
from six import string_types


def parse_json(val):
  """
  Parses json if string else return
  """
  if isinstance(val, string_types):
    return json.loads(val)
  return val


@frappe.whitelist()
def batch_update(docs, commit_each_doc=True):
  """
      docs Format:
      [
          "Contract (DocType)": {
              "create": [
                  {
                      "fieldname": value,
                      "fieldname": value,
                      "fieldname": value
                  }
              ],
              "update":[
                  {
                      "fieldname": value,
                      "fieldname": value,
                      "fieldname": value
                  }
              ],
              "delete": [
                  {
                      "name": name_of_document 
                  }
              ]
          },
          "Another (DocType)": {

          }
      ]
      @return updated_docs_data , failds_data
  """
  failed = []
  action_map = frappe._dict({
      "delete": ['delete', 'cancelDelete'],
      "submit": ['submit', 'saveSubmit', 'createSubmit'],
      "cancel": ['cancel', 'cancelDelete']
  })
  action_map.save = ['create', 'save',
                     'update', 'edit'] + action_map.submit[1:]
  action_map.all = action_map.save + action_map.delete + action_map.cancel
  for doctype, action_objs in parse_json(docs).items():
    for action, list_data in action_objs.items():
      for data in list_data:
        if data.get('name'):
          doc = frappe.get_doc(doctype, data.get('name'))
        else:
          doc = frappe.new_doc(doctype)
        try:
          if action not in action_map.all:
            failed.append(data.update({"error": _(
                "Action '{}' not correct, Action should be in '{}'".format(action, ', '.join(action_map.all)))}))
            continue

          if action in action_map.save:
            doc.update(data)
            doc.save()
          elif action in action_map.cancel and doc.docstatus == 1:
            doc.cancel()
          if action in action_map.submit:
            doc.submit()
          if action in action_map.delete:
            doc.delete()

          if action not in action_map.delete:
            doc.reload()
          data.update(doc.as_dict())
          if commit_each_doc:
            frappe.db.commit()
        except Exception as e:
          failed.append(data.update({"error": e}))
          if commit_each_doc:
            frappe.db.rollback()
          else:
            raise
  return docs, failed, commit_each_doc
