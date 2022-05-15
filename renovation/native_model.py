from asyncer import asyncify
from typing import Optional, List

import frappe
from frappe.model.document import Document


class FrappeDocType:
    _doc: Document = None

    def __init__(
        self,
        doctype: Optional[str] = None,
        doc: Optional[Document] = None
    ):
        if isinstance(doctype, str):
            self._doc = frappe.new_doc(doctype)
        elif doc:
            self._doc = doc
        else:
            raise Exception("Please provide doctype or document object to initialize FrappeDocType")

    def __getattr__(self, name: str):
        return getattr(self._doc, name, None)

    def __setattr__(self, name: str, value):
        if name == "_doc":
            self.__dict__["_doc"] = value
        elif self._doc and self._doc.meta.get_field(name):
            self._doc.set(name, value)

    async def reload(self):
        return await asyncify(self._doc.reload)()

    async def insert(self, *args, **kwargs):
        return await asyncify(self._doc.insert)(*args, **kwargs)

    async def save(self, *args, **kwargs):
        return await asyncify(self._doc.save)(*args, **kwargs)

    async def submit(self, *args, **kwargs):
        return await asyncify(self._doc.submit)(*args, **kwargs)

    async def cancel(self, *args, **kwargs):
        return await asyncify(self._doc.cancel)(*args, **kwargs)

    async def delete(self, *args, **kwargs):
        return await asyncify(self._doc.delete)(*args, **kwargs)

    async def db_get(self, *args, **kwargs):
        return await asyncify(self._doc.db_get)(*args, **kwargs)

    async def db_set(self, *args, **kwargs):
        return await asyncify(self._doc.db_set)(*args, **kwargs)

    @classmethod
    async def get_doc(cls, doctype: str, docname: str):
        """
        Returns a wrapped FrappeDocType
        """
        doc = await asyncify(frappe.get_doc)(doctype, docname)
        return cls(doc=doc)

    @classmethod
    async def get_all(
            cls,
            doctype: str,
            filters: dict = None,
            fields: List[str] = ["name"],
            offset: int = 0,
            count: int = 10,
            order_by: str = None) -> List[dict]:
        return await asyncify(frappe.get_all)(
            doctype, filters=filters, fields=fields, limit_start=offset,
            limit_page_length=count, order_by=order_by)

    @classmethod
    async def db_set_value(cls, doctype: str, docname: str, fieldname: str, value):
        return await asyncify(frappe.db.set_value)(
            doctype, docname, fieldname, value)

    @classmethod
    async def db_get_value(cls, doctype: str, docname: str, fieldname: str = "name", as_dict=None):
        return await asyncify(frappe.db.get_value)(
            doctype, docname, fieldname, as_dict=as_dict
        )

    @classmethod
    async def exists(cls, doctype: str, docname: str):
        return await asyncify(frappe.db.exists)(doctype, docname)
