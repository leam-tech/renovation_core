import frappe
from frappe.utils import add_to_date, now_datetime

from .auth import get_bearer_token
from .images import is_image_path


@frappe.whitelist()
def get_attachments(doctype, name, only_images=False, ignore_permissions=False):
  fields = ["name", "file_name", "file_url", "file_size",
            "content_hash", "folder", "thumbnail_url", "is_private"]
  filters = {"attached_to_doctype": doctype, "attached_to_name": name}
  att = frappe.get_all("File", filters=filters, fields=fields) if ignore_permissions else \
      frappe.get_list("File", filters=filters, fields=fields)

  ret = []
  for f in att:
    if (only_images and is_image_path(f.file_name)) or not only_images:
      ret.append(f)
  return ret


@frappe.whitelist(allow_guest=True)
def get_download_url(file_url, expires_in=None):
  try:
    _file = frappe.get_doc("File", {"file_url": file_url})
    if not is_downloadable_file(_file):
      raise frappe.PermissionError

    url = None
    if _file.is_private:
      token = get_bearer_token(frappe.session.user, expires_in=expires_in or 3 * 60 * 60)
      url = "{}?token={}".format(file_url, token["access_token"])
    else:
      url = file_url

    return {
        "status": "success",
        "url": url
    }

  except frappe.PermissionError:
    frappe.msgprint("You don't have enough permissions to download the file")
    return {
        "status": "forbidden",
        "msg": "You dont have enough permission to download the file"
    }


def is_downloadable_file(file):
  if file.is_private:
    return (frappe.has_permission("File", ptype="read", doc=file.name)
            or frappe.has_permission(file.attached_to_doctype, ptype="read", doc=file.attached_to_name))
  return True
