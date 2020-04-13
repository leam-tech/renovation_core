import frappe


def apply_docdefaults(data, doc, doctype, evaluation_time="Normal"):
  # get docdefault doc name
  defaults = frappe.get_value(
      'Renovation DocDefaults', filters={'dt': doctype})
  if defaults:
    defaults = frappe.get_all(
        'Renovation DocDefault Items', fields="*", filters={'parent': defaults})
  else:
    defaults = []

  # method resolved defaults
  calculated_defaults = []

  # apply defaults without overwriting
  for field in defaults:
    if field.evaluation_time != evaluation_time:
      continue

    if field.get_value_from == "Static Value":
      set_field_value(doc, field.fieldname, field.link_default_value if field.fieldtype ==
                      "Link" else field.default_value, field.override)
    elif field.get_value_from == "Method" or field.get_value_from == "Evaluate":
      calculated_defaults.append(field)

  # have to fetch child docs and apply the same on it
  # fetch all fields of this doctype and call this function over for child tables
  table_docfields = frappe.get_all('DocField', fields=[
                                   'name', 'fieldname', 'options'], filters={'parent': doctype, 'fieldtype': 'Table'})
  for child_table_field in table_docfields:
    children = data.get(child_table_field.fieldname, [])
    if not isinstance(children, (list, tuple)):
      continue
    for child_doc in children:
      apply_docdefaults(child_doc, doc, child_table_field.options)

  # calculate method fields after everything
  for field in calculated_defaults:
    if field.get_value_from == "Method":
      f = frappe.get_attr(field.method)
      params = eval('(' + field.parameter + ')') if field.parameter else None
      set_field_value(doc, field.fieldname, f(*params)
                      if field.parameter else f(), field.override)
    elif field.get_value_from == "Evaluate":
      set_field_value(doc, field.fieldname, eval(
          field.eval_code), field.override)


def set_field_value(doc, fieldname, value, override=False):
  if override:
    doc.update({fieldname: value})
  else:
    if not doc.get(fieldname):
      doc.update({fieldname: value})
