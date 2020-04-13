import frappe
from frappe.desk.form.load import get_meta_bundle
from frappe.model.utils.user_settings import get_user_settings


@frappe.whitelist(allow_guest=True)
def get_bundle(doctype, user=None):
  if not user:
    user = frappe.session.user
  cache_key = "{}:{}".format(doctype, user)
  bundle_obj = frappe.cache().hget("renovation_doc_bundle", cache_key)
  if not bundle_obj:
    bundle_obj = {
        "metas": [],
        "user_settings": get_user_settings(doctype)
    }

    # update renovation_enabled
    for meta in get_meta_bundle(doctype):
      enabled_fields = get_enabled_fields(meta.name, user)
      meta = frappe._dict(meta.as_dict())
      # renovation-core takes 1 as true since all other db-Check types are 0/1
      meta.treeview = 1 if meta.name in frappe.get_hooks("treeviews") else 0

      fields = []
      _fields = []
      for field in meta.get("fields"):
        if field.get("fieldname") in enabled_fields:
          fields.append(field)
        else:
          _fields.append(field)
      meta["fields"] = fields
      meta["_fields"] = _fields
      bundle_obj["metas"].append(meta)

      # Renovation Scripts
      meta["renovation_scripts"] = frappe.get_all(
          "Renovation Script", filters={"target_dt": meta.name}, fields=["name", "code"])

      # reference bundle so that it can be cleared when required
      # a doctype can be referenced in multiple bundles
      mcach_key = "{}:{}".format(meta.name, user)
      ref_bundles = frappe.cache().hget("renovation_doc_ref_bundle", mcach_key)
      if not ref_bundles:
        ref_bundles = []
      if doctype not in ref_bundles:
        ref_bundles.append(doctype)
        frappe.cache().hset("renovation_doc_ref_bundle", mcach_key, ref_bundles)

    frappe.cache().hset("renovation_doc_bundle", cache_key, bundle_obj)
  return bundle_obj


def get_enabled_fields(doctype, user=None, role_profile=None):
  """
  Priority
  1.User
  2.Role Profile
  3.Global
  """
  if not user:
    user = frappe.session.user
  if not role_profile:
    role_profile = frappe.db.get_value('User', user, 'role_profile_name')
  enabled_fields = set([x.fieldname for x in frappe.get_all("Renovation DocField", fields=[
                       "fieldname"], filters={"renovation_enabled": 1, "p_doctype": doctype})])
  override_as_global = frappe.db.get_value('User', user, 'override_as_global')
  if override_as_global:
    return enabled_fields
  if role_profile:
    role_profile_enable, role_profile_disable = get_enable_and_disable_fields(
        doctype, 'Role Profile', 'role_profile', role_profile)
    for f in role_profile_disable:
      if f in enabled_fields:
        enabled_fields.remove(f)
    enabled_fields.update(role_profile_enable)

  user_enable, user_disable = get_enable_and_disable_fields(
      doctype, 'User', 'user', user)
  for f in user_disable:
    if f in enabled_fields:
      enabled_fields.remove(f)
  enabled_fields.update(user_enable)

  return enabled_fields


def get_enable_and_disable_fields(doctype, user_or_role_profile, field, value):
  enable, disable = [], []
  enable_and_disable = frappe.db.sql("""select p.fieldname, ct.enabled from `tabRenovation DocField {}` ct
			left join `tabRenovation DocField` p on ct.parent = p.name
			where ct.{}='{}' and p.p_doctype='{}'"""
                                     .format(user_or_role_profile, field, value, doctype), as_dict=True)
  for f in enable_and_disable:
    if f.enabled:
      enable.append(f.fieldname)
    else:
      disable.append(f.fieldname)
  return enable, disable


def clear_meta_cache(doctype):
  keys = []
  for k in frappe.cache().hkeys("renovation_doc_bundle"):
    k = frappe.safe_decode(k)
    if k.startswith("{}:".format(doctype)):
      frappe.cache().hdel("renovation_doc_bundle", k)
  frappe.cache().hdel("renovation_doc_bundle", doctype)
  ref_bundles = []
  for key in keys:
    ref_bundles += frappe.cache().hget("renovation_doc_ref_bundle", key) or []

  for dt in ref_bundles:
    frappe.cache().hdel("renovation_doc_bundle", dt)


def clear_all_meta_cache():
  for k in frappe.cache().hkeys("renovation_doc_bundle"):
    frappe.cache().hdel("renovation_doc_bundle", k)
  for k in frappe.cache().hkeys("dashboard"):
    frappe.cache().hdel("dashboard", k)

  frappe.cache().hdel("dashboard_list", frappe.session.user)


def on_renovation_script_change(doc, method):
  clear_meta_cache(doc.target_dt)
