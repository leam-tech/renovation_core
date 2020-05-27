import frappe

"""
Temporary File {
  file: Attach
  target_doctype: Link/DocType
  target_docname: DynamicLink/target_doctype
  target_fieldname: Data
}
"""


def flush_files():
  """
  Go through each Temporary File and check if it has gone past the expiry time or has been attached to some other document
  If it is expired, delete both the actual File and the temporary File
  If the file has been attached to some other document, delete this Temporary File only.

  This function is called attached to the scheduler to be invoked every hour
  """
  temp_files = frappe.get_all("Temporary File", fields=["*"])
  if not len(temp_files):
    return

  for t in temp_files:
    if file_exists(dt=t.target_doctype, dn=t.target_docname, df=t.target_fieldname, file=t.file):
      frappe.delete_doc("Temporary File", t.name)
    elif temp_file_expired(t):
      safe_delete_file(t.file)
      frappe.delete_doc("Temporary File", t.name)


def file_exists(dt, dn, df, file):
  """
  Checks if the file has been linked to the specified document or not.

  :param dt: The doctype to check in
  :param dn: The docname to check in
  :param df: The fieldname to check in
  :param file: the file_url to check for
  """
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
  """
  Checks if the TempFile has lived past its expiry

  :param temp_file {
    creation: datetime
    expires_in_hours: int
    name: string
  }
  """
  from frappe.utils import add_to_date, cint, now_datetime

  if add_to_date(temp_file.creation, hours=cint(temp_file.expires_in_hours) or 5) >= now_datetime():
    return True

  return False


def safe_delete_file(file_url):
  """
  Delete the File iff it has'nt been attached to any other docs
  :param file_url: the file_url to check against
  """
  file_id = frappe.db.get_value("File", {"file_url": file_url})
  if not file_id:
    return

  frappe.delete_doc("File", file_id)
