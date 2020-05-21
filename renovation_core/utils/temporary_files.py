import frappe

"""
Temporary File {
  file: Attach
  target_dt: Link/DocType
  targent_dn: DynamicLink/target_dt
  target_df: Data
}
"""


def flush_files():
  temp_files = frappe.get_all("Temporary File", fields=["*"])
  if not len(temp_files):
    return

  for t in temp_files:
    if file_exists(dt=t.target_dt, dn=t.targent_dn, df=t.target_df, file=t.file):
      frappe.delete_doc("Temporary File", t.name)
    elif temp_file_expired(t):
      safe_delete_file(t.file)
      frappe.delete_doc("Temporary File", t.name)


def file_exists(dt, dn, df, file):
  r = frappe.db.sql("""
    SELECT
      d.name
    FROM `tab{}` d
    WHERE {}=%(file)s
  """.format(dt, df), {"file": file}, as_dict=1)

  if dn:
    r = [x for x in r if x.name == dn]

  return len(r) > 0


def temp_file_expired(temp_file):
  from frappe.utils import add_to_date, cint, now_datetime

  if add_to_date(temp_file.creation, hours=cint(temp_file.expires_in_hours) or 5) >= now_datetime():
    return True

  return False


def safe_delete_file(file_url):
  file_id = frappe.db.get_value("File", {"file_url": file_url})
  if not file_id:
    return
  
  frappe.delete_doc("File", file_id)
