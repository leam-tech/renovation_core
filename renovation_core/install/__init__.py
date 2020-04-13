import os

import frappe
from frappe import _
from jinja2 import Environment, PackageLoader


def get_jinja_env():
  return Environment(loader=PackageLoader("renovation_core.install"))


def check_require_app_installed():
  path = os.path.abspath(os.path.join(
      '..', 'apps', frappe.flags.in_install, 'requirements.txt'))
  with open(path) as f:
    requires = f.read().strip().split('\n')
  installed_apps = frappe.get_installed_apps()
  for req_app in requires:
    if req_app not in installed_apps:
      frappe.throw(_("Please Install {} App.").format(req_app))


def check_except_apps():
  if not frappe.flags.in_install:
    return
  except_apps = frappe.get_hooks('install_except_apps', [])
  installed_apps = frappe.get_installed_apps()
  if frappe.flags.in_install in except_apps:
    frappe.throw(_("App {} excepted by others installed app").format(
        frappe.flags.in_install))
  for exct_app in frappe.get_hooks('install_except_apps', [], frappe.flags.in_install):
    if exct_app in installed_apps:
      frappe.throw(
          _("Except app '{}' already installl on this site.".format(exct_app)))
