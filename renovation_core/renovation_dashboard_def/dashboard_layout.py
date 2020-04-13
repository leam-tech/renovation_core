import frappe
from frappe.utils import cint

from .utils import get_docs_with_role


@frappe.whitelist(allow_guest=True)
def get_dashboard_layout(layout=None, user=None):
  if not user:
    user = frappe.session.user
  if not layout:
    layout = get_default_user_layout(user)

  p = process_layout(layout)

  return p


@frappe.whitelist(allow_guest=True)
def get_user_dashboard_layouts(user=None):
  if not user:
    user = frappe.session.user

  layouts = get_docs_with_role(
      "Renovation Dashboard Layout",
      ["name", "title"],
      "and `tabRenovation Dashboard Layout`.enabled = 1",
      order_by="priority desc",
      user=user
  )

  layouts.extend(frappe.db.get_all(
      "Renovation Dashboard Layout",
      filters={
          "is_user_custom": 1,
          "user": user
      }))

  return layouts


def get_default_user_layout(user=None):
  if not user:
    user = frappe.session.user
  cache = frappe.cache().hget("user_dashboard_layout", user)
  if cache:
    return cache

    # check for custom dashes first
  custom = frappe.db.get_all(
      "Renovation Dashboard Layout",
      filters={
          "is_user_custom": 1,
          "user": user
      })
  if len(custom) > 0:
    layout = custom[0].name
  else:
    # get list of allowed layouts
    layouts = get_docs_with_role(
        "Renovation Dashboard Layout",
        ["name"],
        "and `tabRenovation Dashboard Layout`.enabled = 1",
        order_by="priority desc",
        user=user
    )

    if len(layouts) == 0:
      layout = None
    else:
      layout = layouts[0].name

    if layout:
      frappe.cache().hset("user_dashboard_layout", user, layout)

  return layout


def process_layout(layout):
  if not layout:
    return None

  # wait_for_attach()
  doc = frappe.cache().hget("dashboard_layout", layout)
  if not doc:
    doc = frappe.get_doc("Renovation Dashboard Layout", layout)
    frappe.cache().hset("dashboard_layout", layout, doc)
  dashboards = []
  for d in doc.dashboards or []:
    dash = frappe.get_doc("Renovation Dashboard", d.dashboard)
    obj = {"width": d.width, "height": d.height}
    obj.update(dash.get_chart_meta())
    dashboards.append(obj)

  return {
      "title": doc.title,
      "name": doc.name,
      "can_resize_items": cint(doc.get("can_resize_items", 1)) == 1,
      "can_rearrange_items": cint(doc.get("can_rearrange_items", 1)) == 1,
      "enabled": doc.enabled,
      "priority": doc.priority,
      "dashboards": dashboards
  }
