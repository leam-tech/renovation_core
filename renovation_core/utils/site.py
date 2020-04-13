import os
import subprocess

import frappe
from frappe.utils import cint

# keys
migration_status_key = "renovation_migration_status"
migration_error_key = "renovation_migration_error"
# redis values
migration_status_migrating = "migrating"
migration_status_done = "done"
migration_status_error = "error"


@frappe.whitelist(allow_guest=True)
def get_versions():
  from frappe.utils.change_log import get_versions
  return get_versions()


@frappe.whitelist()
def update_app(app):
  check_if_admin()
  can_migrate()

  if app not in frappe.get_installed_apps():
    frappe.throw("App not installed in this site: {}".format(app or ""))

  app_path = os.path.dirname(frappe.get_app_path(app))
  try:
    return frappe.safe_decode(subprocess.check_output(['git', 'pull'], cwd=app_path, stderr=subprocess.STDOUT))
  except subprocess.CalledProcessError as e:
    return "git-error: {} \n\n {}".format(e.output, app_path)


@frappe.whitelist()
def clear_cache():
  check_if_admin()

  # the following is a copy from frappe.commands.utils
  import frappe.website.render
  from frappe.desk.notifications import clear_notifications
  frappe.clear_cache()
  clear_notifications()
  frappe.website.render.clear_cache()
  return "cache-cleared"


@frappe.whitelist()
def migrate():
  check_if_admin()
  can_migrate()

  status = frappe.safe_decode(frappe.cache().get(migration_status_key))
  error = frappe.safe_decode(frappe.cache().get(migration_error_key))

  if status == migration_status_migrating:
    return "Migration in progress"
  elif status == migration_status_done:
    frappe.cache().set(migration_status_key, migration_status_done + "_seen")
    return {
        "status": "SUCCESS: Last Migration was successfull, Please send a new request to restart migration",
        "error": error
    }
  elif status == migration_status_error:
    frappe.cache().set(migration_status_key, migration_status_error + "_seen")
    return {
        "status": "ERROR: Last Migration wasnt successfull, Please send a new request to retry",
        "error": error
    }

  frappe.enqueue("renovation_core.utils.site.start_migration")
  return {
      "status": "Started migration",
      "last_migration": {
          "status": status,
          "error": error
      }
  }


@frappe.whitelist()
def restart():
  check_if_admin()
  can_migrate()
  # cwd = frappe-bench/sites
  try:
    return frappe.safe_decode(subprocess.check_output(["bench", "restart"], cwd=".."))
  except subprocess.CalledProcessError as e:
    return "restart-error: {}".format(e.output)


def start_migration():
  migration_status = frappe.cache().get(migration_status_key)
  if migration_status == migration_status_migrating:
    # already running
    return

  frappe.cache().set(migration_status_key, migration_status_migrating)
  try:
    from frappe.migrate import migrate
    migrate(verbose=False)
    frappe.cache().set(migration_status_key, migration_status_done)
  except Exception as e:
    frappe.cache().set(migration_status_key, migration_status_error)
    frappe.cache().set(migration_error_key, "error: " + frappe.get_traceback())


def check_if_admin():
  if frappe.session.user != "Administrator":
    frappe.throw("You have to be an administrator to do this")


def can_migrate():
  if not cint(frappe.get_conf().get("migrate_over_http", 0)):
    frappe.throw("Please set migrate_over_http: 1 in site conf")
