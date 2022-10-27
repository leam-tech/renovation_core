from fastapi import APIRouter, HTTPException
from starlette.responses import Response

import frappe


router = APIRouter()


@router.get("/files/{filename}")
def get_public_file(filename: str):

    file_url = f"/files/{filename}"
    name_of_file = frappe.get_value("File", {"file_url": file_url}, "name")
    file = frappe.get_doc("File", name_of_file)
    return Response(content=file.get_content(), media_type="image")


@router.get("/private/files/{filename}")
def get_private_file(filename: str):

    if frappe.session.user == "Guest":
        raise HTTPException(status_code=401, detail="Not allowed")

    file_url = f"/private/files/{filename}"
    name_of_file = frappe.get_value("File", {"file_url": file_url}, "name")
    file = frappe.get_doc("File", name_of_file)
    return Response(content=file.get_content(), media_type="image")
