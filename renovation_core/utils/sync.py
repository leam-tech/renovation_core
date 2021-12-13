import os

import frappe


def _get_doc_files(files, start_path, force=0, sync_everything=False, verbose=False):
  if files is None:
    files = []
  """walk and sync all doctypes and pages"""

  # load in sequence - warning for devs
  document_types = ['doctype', 'page', 'report', 'dashboard_chart_source', 'print_format',
    'website_theme', 'web_form', 'web_template', 'notification', 'print_style',
    'data_migration_mapping', 'data_migration_plan', 'workspace',
    'onboarding_step', 'module_onboarding']
  document_types = document_types + ['renovation_dashboard']

  for doctype in document_types:
    doctype_path = os.path.join(start_path, doctype)
    if os.path.exists(doctype_path):

      for docname in os.listdir(doctype_path):
        if os.path.isdir(os.path.join(doctype_path, docname)):
          doc_path = os.path.join(doctype_path, docname, docname) + ".json"
          if os.path.exists(doc_path):
            if not doc_path in files:
              files.append(doc_path)
  return files


def process(self):
  # don't process for special doctypes
  # prevent's circular dependency
  if frappe.db and frappe.db.exists("DocType", "Property Setter") and "DocPerm" in self.special_doctypes:
    sdoc = list(self.special_doctypes)
    sdoc.remove("DocPerm")
    self.special_doctypes = tuple(sdoc)
  if self.name in self.special_doctypes:
    return

  self.add_custom_fields()
  self.apply_property_setters()
  self.sort_fields()
  self.get_valid_columns()
  self.set_custom_permissions()
