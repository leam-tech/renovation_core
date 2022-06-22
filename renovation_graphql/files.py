from asyncer import asyncify

from starlette.datastructures import UploadFile
from starlette.requests import FormData

import frappe
from frappe.handler import ALLOWED_MIMETYPES

from renovation import cint
import renovation


async def make_file_document(
        file_key, model=None, name=None, fieldname=None, is_private=None,
        ignore_permissions=False):
    user = None
    if not ignore_permissions and frappe.session.user == 'Guest':
        if frappe.get_system_settings('allow_guests_to_upload_files'):
            ignore_permissions = True
        else:
            raise frappe.PermissionError("Guest uploads are not allowed")
    else:
        user = frappe.get_doc("User", frappe.session.user)

    form: FormData = renovation.local.request_form
    file: UploadFile = form.get(file_key)
    if not file:
        return

    content = await file.read()
    filename = file.filename

    frappe.local.uploaded_file = content
    frappe.local.uploaded_filename = filename

    if frappe.session.user == 'Guest' or (user and not user.has_desk_access()):
        import mimetypes
        filetype = mimetypes.guess_type(filename)[0]
        if filetype not in ALLOWED_MIMETYPES:
            frappe.throw(frappe._("You can only upload JPG, PNG, PDF, or Microsoft documents."))

    ret = frappe.get_doc({
        "doctype": "File",
        "attached_to_doctype": model,
        "attached_to_name": name,
        "attached_to_field": fieldname,
        "file_name": filename,
        "is_private": cint(is_private),
        "content": content
    })
    await asyncify(ret.save)(ignore_permissions=ignore_permissions)

    doc = ret.as_dict()
    doc.attached_to_model = doc.attached_to_doctype

    return doc
