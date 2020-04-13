import json

import frappe
from renovation_core.renovation_core.doctype.renovation_docfield.renovation_docfield import \
  toggle_enabled as enable_field
from six import string_types


@frappe.whitelist()
def update_values(values, action_for, user=None, role_profile=None):
  if isinstance(values, string_types):
    values = json.loads(values)
  for doctype, fields in values.items():
    for fieldname in fields or []:
      if action_for == "Global":
        enable_field(doctype, fieldname, 1)
      elif action_for == "User":
        enable_field(doctype, fieldname, 1, user, ignore_parent_update=True)
      elif action_for == "Role Profile":
        enable_field(doctype, fieldname, 1,
                     role_profile=role_profile, ignore_parent_update=True)

    if action_for == "Global":
      frappe.db.sql("""update `tabRenovation DocField` set renovation_enabled=0 
			where p_doctype = '{}' and fieldname not in ('{}')""".format(doctype, "', '".join(fields)))
    elif action_for == "User":
      frappe.db.sql("""update `tabRenovation DocField User` ct
		 left join `tabRenovation DocField` p on ct.parent = p.name
		 set ct.enabled=0 
		 where ct.user='{}' and p.p_doctype='{}' and p.fieldname not in ('{}')"""
                    .format(user, doctype, "', '".join(fields)))
    elif action_for == "Role Profile":
      frappe.db.sql("""update `tabRenovation DocField Role Profile` ct
		 left join `tabRenovation DocField` p on ct.parent = p.name
		 set ct.enabled=0 
		 where ct.role_profile='{}' and p.p_doctype='{}' and p.fieldname not in ('{}')"""
                    .format(role_profile, doctype, "', '".join(fields)))
  return


@frappe.whitelist()
def get_docfield_and_selected_val(doctype, user=None, role_profile=None):
  return {
      "doctypes_fields": get_doctypes_fields(doctype),
      "selected_values": get_all_enable_fields(doctype, user, role_profile)
  }


def get_all_enable_fields(doctype, user=None, role_profile=None):
  meta = frappe.get_meta(doctype)
  cdoctypes = [x.options for x in meta.fields if x.fieldtype == "Table"]
  cdoctypes.append(doctype)
  global_val = frappe.get_all("Renovation DocField", {"p_doctype": (
      'in', cdoctypes), "renovation_enabled": 1}, ['p_doctype', 'fieldname', 'name'])
  g_val = get_map_data(global_val)

  user_data = {}
  if user:
    user_data = get_map_data(frappe.db.sql("""select p.p_doctype, p.fieldname from `tabRenovation DocField User` ct
		 left join `tabRenovation DocField` p on ct.parent = p.name
		 where ct.user='{}' and p.p_doctype in ('{}')""".format(user, "', '".join(cdoctypes)), as_dict=True))

  role_profile_data = {}
  if role_profile:
    role_profile_data = get_map_data(frappe.db.sql("""select p.p_doctype, p.fieldname from `tabRenovation DocField Role Profile` ct
		 left join `tabRenovation DocField` p on ct.parent = p.name
		 where ct.role_profile='{}' and p.p_doctype in ('{}')""".format(role_profile, "', '".join(cdoctypes)), as_dict=True))
  return {
      "Global": g_val,
      "User": user_data,
      "Role Profile": role_profile_data
  }


def get_map_data(data):
  map_data = {}
  for x in data:
    d = map_data.setdefault(x.p_doctype, [])
    d.append(x.fieldname)
  return map_data


@frappe.whitelist()
def get_doctypes_fields(doctype):
  meta = frappe.get_meta(doctype)
  cdoctypes = [x.options for x in meta.fields if x.fieldtype == "Table"]
  doc_map = {doctype: meta.fields}
  for d in cdoctypes:
    doc_map[d] = frappe.get_meta(d).fields
  return doc_map
