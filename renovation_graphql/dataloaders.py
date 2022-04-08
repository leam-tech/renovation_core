from typing import List, Union, Tuple
from asyncer import asyncify
from aiodataloader import DataLoader
from collections import OrderedDict

import frappe

import renovation
from renovation import RenovationModel


def get_model_dataloader(model: Union[RenovationModel, str]) -> DataLoader:
    doctype = model
    if not isinstance(doctype, str):
        doctype = model.get_doctype()

    loader = _get_loader_from_locals(doctype)
    if loader:
        return loader

    loader = DocTypeDataLoader(doctype=doctype)
    renovation.local.dataloaders[doctype] = loader
    return loader


def get_child_table_dataloader(
        child_model: Union[RenovationModel, str],
        parent_model: Union[RenovationModel, str],
        parent_field: str) -> DataLoader:

    child_dt = child_model
    if not isinstance(child_dt, str):
        child_dt = child_model.get_doctype()

    parent_dt = parent_model
    if not isinstance(parent_model, str):
        parent_dt = parent_model.get_doctype()

    locals_key = (child_dt, parent_dt, parent_field)
    loader = _get_loader_from_locals(locals_key)
    if loader:
        return loader

    loader = ChildDocTypeDataLoader(
        child_dt=child_dt,
        parent_dt=parent_dt,
        parent_field=parent_field,
    )

    renovation.local.dataloaders[locals_key] = loader
    return loader


def _get_loader_from_locals(key: Union[str, Tuple[str]]):
    if not hasattr(renovation.local, "dataloaders"):
        renovation.local.dataloaders = renovation._dict()

    if key in renovation.local.dataloaders:
        return renovation.local.dataloaders.get(key)


class DocTypeDataLoader(DataLoader):
    def __init__(self, doctype):
        super().__init__()
        self.doctype = doctype

    async def batch_load_fn(self, keys: List[str]):
        docs = await asyncify(frappe.get_all)(
            doctype=self.doctype,
            filters=[["name", "IN", keys]],
            fields=["*"],
            limit_page_length=len(keys) + 1
        )

        sorted_docs = []
        for k in keys:
            doc = [x for x in docs if x.name == k]
            if not len(doc):
                sorted_docs.append(None)
                continue

            sorted_docs.append(doc[0])
            docs.remove(doc[0])

        return sorted_docs


class ChildDocTypeDataLoader(DataLoader):
    def __init__(self, child_dt, parent_dt: str, parent_field: str):
        super().__init__()
        self.child_dt = child_dt
        self.parent_dt = parent_dt
        self.parent_field = parent_field

    async def batch_load_fn(self, keys: List[str]):

        rows = await asyncify(frappe.db.sql)(f"""
        SELECT * FROM `tab{self.child_dt}`
        WHERE
            parent IN %(parent_keys)s
            AND parenttype = %(parenttype)s
            AND parentfield = %(parentfield)s
        ORDER BY idx
        """, dict(
            parent_keys=keys,
            parenttype=self.parent_dt,
            parentfield=self.parent_field,
        ), as_dict=1)

        _results = OrderedDict()
        for k in keys:
            _results[k] = []

        for row in rows:
            if row.parent not in _results:
                continue
            _results.get(row.parent).append(row)

        return _results.values()
