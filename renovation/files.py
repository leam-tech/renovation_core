from fastapi import APIRouter, HTTPException
from asyncer import asyncify
from starlette.responses import Response

import frappe


router = APIRouter()


@router.get("/files/{filename}")
async def get_public_file(filename: str):
    return await get_file_as_response(f"/files/{filename}")


@router.get("/private/files/{filename}")
async def get_private_file(filename: str):

    if frappe.session.user == "Guest":
        raise HTTPException(status_code=401, detail="Not allowed")

    return await get_file_as_response(f"/private/files/{filename}")


async def get_file_as_response(file_url: str):

    name_of_file = await asyncify(frappe.get_value)("File", {"file_url": file_url}, "name")

    if not name_of_file:
        raise HTTPException(status_code=404, detail="Not found")

    file = await asyncify(frappe.get_doc)("File", name_of_file)

    import mimetypes
    filetype = mimetypes.guess_type(file.file_url)[0]
    file_content = await asyncify(file.get_content)()

    return Response(content=file_content, media_type=filetype)
