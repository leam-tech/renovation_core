import frappe

from .utils import get_docs_with_role


@frappe.whitelist(allow_guest=True)
def get_all_dashboard_meta(user=None, **kwargs):
  dashboards = get_permitted_dashboard(user=user)
  metas = []
  for dash in dashboards:
    metas.append(get_dashboard_meta(dash.name))

  return metas


@frappe.whitelist(allow_guest=True)
def get_dashboard_data(dashboard, user=None, **kwargs):
  dashboards = get_permitted_dashboard(user=user)
  if dashboard not in [dash.name for dash in dashboards]:
    raise frappe.PermissionError
  cache_key = dashboard
  cache = frappe.cache().hget("dashboard", cache_key)
  if cache:
    return cache

  frappe.log("Not serving from cache")
  doc = frappe.get_doc("Renovation Dashboard", dashboard)
  data = doc.ready_chart_data(**kwargs)
  if data and not doc.get("custom_caching", 0):
    frappe.cache().hset('dashboard', cache_key, data)
  return data


@frappe.whitelist()
def get_dashboard_meta(dashboard):
  meta = frappe.cache().hget("dashboard", "{}_meta".format(dashboard))
  if not meta:
    meta = frappe.get_doc(
        "Renovation Dashboard", dashboard).get_chart_meta()
    frappe.cache().hset("dashboard", "{}_meta".format(dashboard), meta)
  return meta


def get_permitted_dashboard(parent="Renovation Dashboard", user=None):
  if not user:
    user = frappe.session.user
  if frappe.cache().hget('dashboard_list', user):
    return frappe.cache().hget('dashboard_list', user)

  dashboards = get_docs_with_role(
      "Renovation Dashboard",
      ["name", "title", "modified"],
      condition="and `tabRenovation Dashboard`.enable=1",
      user=user,
      include_if_no_role=True
  )

  frappe.cache().hset('dashboard_list', user, dashboards)
  return dashboards


def get_custom_dashboard_cache_data(custom_key):
  return frappe.cache().hget("dashboard", custom_key)


def set_custom_dashboard_cache_data(custom_key, data):
  frappe.cache().hset("dashboard", custom_key, data)


def clear_custom_dashboard_cache_data(custom_key):
  frappe.cache().hdel("dashboard", custom_key)
