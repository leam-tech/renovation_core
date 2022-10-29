from fastapi import APIRouter, HTTPException
from starlette.responses import Response

import frappe


router = APIRouter()


@router.get("/files/{filename}")
def get_public_file(filename: str):
    return get_file_as_response(f"/files/{filename}")


@router.get("/private/files/{filename}")
def get_private_file(filename: str):

    if frappe.session.user == "Guest":
        raise HTTPException(status_code=401, detail="Not allowed")

    return get_file_as_response(f"/private/files/{filename}")


def get_file_as_response(file_url: str):

    name_of_file = frappe.get_value("File", {"file_url": file_url}, "name")
    file = frappe.get_doc("File", name_of_file)

    import mimetypes
    filetype = mimetypes.guess_type(file.file_url)[0]

    return Response(content=file.get_content(), media_type=filetype)
