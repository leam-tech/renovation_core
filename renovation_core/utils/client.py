import frappe


@frappe.whitelist(allow_guest=True)
def get_current_user_roles():
  return frappe.get_roles(frappe.session.user)


@frappe.whitelist(allow_guest=True)
def get_current_user_permissions():
  info = frappe.get_user().load_user()
  ret = frappe._dict()
  for k in ['can_print', 'can_set_user_permissions', 'can_create', 'can_search', 'can_export', 'can_get_report',
            'can_write', 'can_import', 'can_email', 'can_cancel', 'can_delete', 'can_read']:
    ret[k] = info.get(k)
  return ret


@frappe.whitelist()
def get_default(key, parent="__default"):
  defaults = frappe.defaults.get_defaults_for(parent)
  return defaults.get(key, None)


@frappe.whitelist(allow_guest=True)
def get_lang_dict(lang=None):
  if lang:
    # frappe.get_lang_dict uses this variable internally
    frappe.local.lang = lang

  messages = frappe.get_lang_dict("boot")

  # load translated report names
  for name in frappe.boot.get_allowed_reports():
    messages[name] = frappe._(name)

  # only untranslated
  messages = {k: v for k, v in messages.items() if k != v}

  for hook in frappe.get_hooks("extend_translation"):
    frappe.get_attr(hook)(messages=messages)

  return messages


@frappe.whitelist()
def get_boot_user_info():
  # used for listing the people in Comment mentions
  from frappe.boot import get_fullnames
  return get_fullnames()
