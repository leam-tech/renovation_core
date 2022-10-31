import os
from fastapi import APIRouter, HTTPException
from starlette.responses import Response
from asyncer import asyncify

import frappe
from frappe.core.doctype.access_log.access_log import make_access_log


router = APIRouter()


@router.get("/files/{filename}")
async def get_public_file(filename: str):

    file_url = f"/files/{filename}"
    name_of_file = await asyncify(frappe.get_value)("File", {"file_url": file_url}, "name")

    if not name_of_file:
        raise HTTPException(status_code=404, detail="Not found")

    file_doc = await asyncify(frappe.get_doc)("File", name_of_file)

    return await file_content_as_response(file_doc)


@router.get("/private/files/{filename}")
async def get_private_file(filename: str):

    file_url = f"/private/files/{filename}"
    files = frappe.db.get_all("File", {"file_url": file_url})

    if not files:
        raise HTTPException(status_code=404, detail="Not found")

    can_access = False
    file_doc = None
    # Check if can access file though any File doc
    for file in files:

        file_doc = await asyncify(frappe.get_doc)("File", file)
        can_access = file_doc.is_downloadable()

        if can_access:
            make_access_log(
                doctype="File",
                document=file_doc.name,
                file_type=os.path.splitext(filename)[-1][1:])
            break

    if not can_access:
        raise HTTPException(status_code=401, detail="Not allowed")

    return await file_content_as_response(file_doc)


async def file_content_as_response(file_doc):

    import mimetypes
    filetype = mimetypes.guess_type(file_doc.file_url)[0]
    file_content = await asyncify(file_doc.get_content)()

    return Response(content=file_content, media_type=filetype)
