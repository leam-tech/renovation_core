import frappe


def get_docs_with_role(doctype, fields, condition="", order_by="", user=None, include_if_no_role=False):
  if not user:
    user = frappe.session.user

  roles = frappe.get_roles(user)
  if "name" not in fields:
    fields.insert(0, "name")

  if not condition:
    condition = ""

  if order_by:
    order_by = "ORDER BY {}".format(order_by)

  result = []
  column = ", ".join(["`tab{}`.{}".format(doctype, col) for col in fields])
  result.extend(
      frappe.db.sql("""select distinct
              {column}
            FROM `tab{doctype}`, `tabHas Role`
            WHERE
                `tabHas Role`.role in ('{roles}')
                and `tabHas Role`.parent = `tab{doctype}`.name
                and `tabHas Role`.parenttype = '{doctype}'
                {condition}
                {order_by}
        """.format(doctype=doctype, column=column, roles="', '".join(roles), condition=condition, order_by=order_by), as_dict=1)
  )

  if include_if_no_role:
    result.extend(
        frappe.db.sql("""
        select distinct
            {column}
        from `tab{doctype}`
        where
            (select count(*) from `tabHas Role`
            where `tabHas Role`.parent=`tab{doctype}`.name) = 0
            {condition}
            {order_by}
    """.format(doctype=doctype, column=column, condition=condition, order_by=order_by), as_dict=1)
    )

  return result


"""
called from hooks.clear_cache
"""


def clear_dashboard_cache():
  clear_layout_cache()

  # clear permitted dash cache
  for k in frappe.cache().hkeys("dashboard_list"):
    frappe.cache().hdel("dashboard_list", k)


def clear_layout_cache(layout=None):
  for user in frappe.cache().hkeys("user_dashboard_layout"):
    frappe.cache().hdel("user_dashboard_layout", user)
  if layout:
    frappe.cache().hdel("dashboard_layout", layout)


def clear_cache_on_doc_events(doc, method):
  if doc.doctype == "Renovation Dashboard":
    frappe.cache().hdel('dashboard', "%s_meta" % doc.name)
  elif doc.doctype == "Renovation Dashboard Layout":
    clear_layout_cache(doc.name)
  else:
    for dashboard in get_dashboards_for_clear_cache(doc.doctype):
      frappe.cache().hdel('dashboard', dashboard)
      if frappe.db.get_value("Renovation Dashboard", dashboard, "custom_caching"):
        frappe.get_doc("Renovation Dashboard",
                       dashboard).clear_cache_on_doc_events(doc, method)


def get_dashboards_for_clear_cache(doctype):
  try:
    cache_key = '_{}_purge_cache'.format(doctype)
    if frappe.cache().hget('dashboard', cache_key):
      return frappe.cache().hget('dashboard', cache_key)
    data = [x.parent for x in frappe.get_all('Renovation Purge Cache', {
                                             'link_doctype': doctype, 'parenttype': 'Renovation Dashboard'}, 'parent')]
    frappe.cache().hset('dashboard', cache_key, data)
    return data
  except:
    return []
