import frappe
from renovation_core.renovation_core.doctype.renovation_sidebar.renovation_sidebar import RenovationSidebar
from six import string_types

REDIS_USER_SIDEBAR = "user_sidebar"
REDIS_SIDEBAR_TREE = "sidebar_tree"


def clear_cache():
  frappe.cache().delete_value(REDIS_USER_SIDEBAR)
  frappe.cache().delete_value(REDIS_SIDEBAR_TREE)


def clear_sidebar_cache(doc, method):
  frappe.cache().delete_value(REDIS_USER_SIDEBAR)
  frappe.cache().hdel(REDIS_SIDEBAR_TREE, doc.name)


def clear_user_sidebar_cache(doc, method):
  frappe.cache().hdel(REDIS_USER_SIDEBAR, doc.name)


@frappe.whitelist()
def get_sidebar(user=None):
  # wait_for_attach()
  if not user:
    user = frappe.session.user

  user_sidebar = get_user_sidebar(user)

  # if still not present, get legacy
  if not user_sidebar:
    legacy_sidebar = get_legacy_sidebar(user)
    if not legacy_sidebar:
      return None
    s = get_updated_legacy_sidebar(legacy_sidebar)
    s.insert(ignore_permissions=True)
    user_sidebar = s.name

  return {
      "sidebar": user_sidebar,
      "data": get_sidebar_tree(user_sidebar)
  }


def get_sidebar_tree(sidebar_name):
  sidebar = frappe.cache().hget(REDIS_SIDEBAR_TREE, sidebar_name)
  if sidebar:
    return sidebar

  sidebar_doc = frappe.get_doc("Renovation Sidebar", sidebar_name)
  sidebar = []
  group_stack = [sidebar]
  for item in sidebar_doc.items:
    item = item.as_dict()
    if item.nesting_level > len(group_stack) - 1:
      # get the last item and make it as a group
      lastItem = group_stack[-1][-1]
      lastItem.children = []
      group_stack.append(lastItem.children)
    elif item.nesting_level < len(group_stack) - 1:
      group_stack.pop()

    group_stack[item.nesting_level].append(item)

  frappe.cache().hset(REDIS_SIDEBAR_TREE, sidebar_name, sidebar)
  return sidebar


def get_user_sidebar(user=None):
  if not user:
    user = frappe.session.user

  s = frappe.cache().hget(REDIS_USER_SIDEBAR, user)
  if frappe.db.exists("Renovation Sidebar", s):
    return s

  # User.roles doesnt include the role "All" saved in the backend
  # the role "All" wont get joined in the below query

  # Check for sidebars with specific roles
  sidebars = frappe.db.sql("""
	SELECT DISTINCT
		role_sidebar.parent
	FROM `tabHas Role` role_sidebar
		JOIN `tabHas Role` role_user
			ON role_sidebar.role = role_user.role
		WHERE
			role_sidebar.parenttype = "Renovation Sidebar"
			AND role_sidebar.parentfield = "applicable_roles"
			AND role_user.parenttype = "User"
			AND role_user.parent = %(user)s
	""", {"user": user})

  if not len(sidebars):
    # no sidebars found with a specific role attached
    # lets check for a sidebar defined for role 'All'
    sidebars = frappe.db.sql("""
      SELECT DISTINCT
        role_sidebar.parent
      FROM `tabHas Role` role_sidebar
      WHERE
        role_sidebar.parenttype = "Renovation Sidebar"
        AND role_sidebar.role = "All"
        AND role_sidebar.parentfield = "applicable_roles"
      ORDER BY
        creation desc
    """)

  if not len(sidebars):
    return None

  s = sidebars[0][0]
  frappe.cache().hset(REDIS_USER_SIDEBAR, user, s)
  return s


def get_legacy_sidebar(user=None):
  from renovation_core.utils.client import get_default
  if not user:
    user = frappe.session.user

  userSidebar = get_default("renovationSidebar", user)
  if userSidebar:
    return frappe.parse_json(userSidebar)

  globalSidebar = get_default("renovationSidebar")
  if globalSidebar:
    return frappe.parse_json(globalSidebar)

  return None


def get_updated_legacy_sidebar(sidebar):
  s = frappe.new_doc("Renovation Sidebar")  # type: RenovationSidebar
  s.title = "Legacy"
  s.append("applicable_roles", frappe._dict(role="All"))

  def process(items, nesting_level):
    for item in items:
      item = frappe._dict(item)
      d = frappe._dict(nesting_level=nesting_level)
      if item.children:
        d.title = item.label
        s.append("items", d)
        process(item.children, nesting_level + 1)
      else:
        if item.type == "form":
          d.title = item.doctype
          d.target_type = "DocType"
          d.target = item.doctype
        elif item.type == "report":
          d.title = item.report
          d.target_type = "Report"
          d.target = item.report
        s.append("items", d)

  process(sidebar, 0)
  return s


def has_sidebar_permission(doc, ptype, user):
  if ptype == "read":
    return True

  from renovation_core.utils.client import get_default
  perms = get_default("sidebarEditorAccessRoles") or "[]"
  if isinstance(perms, string_types):
    perms = frappe.parse_json(perms)
  perms = [x.get("role") for x in perms]

  intersection = [x for x in frappe.get_roles(user) if x in perms]
  if len(intersection):
    return True

  return False
