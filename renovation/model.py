import inspect
from typing import Union, List, Optional, TypeVar, Generic

import frappe
from frappe.model.document import Document
import asyncer
import asyncio

T = TypeVar("T")

doctype_map = {}


def map_doctype(doctype: str, renovation_class: type):
    global doctype_map
    doctype_map[renovation_class] = doctype


class FrappeModel(Generic[T], Document):
    """
    document.py
    - reload
    - insert
    - save
    - delete
    - update(just instance)
    - Document.hook

    Basic Renovation Lifecycle:
    > New Insert
        - before_insert
        - before_validate
        - validate
        - before_save
        - on_update
        - on_change
        - after_insert
        - on_change: After every operation

    > Updating an existing doc
        - before_validate
        - validate
        - before_save
        - on_update
        - on_change
    """

    def __init__(self, *args, **kwargs) -> None:
        if not args and not kwargs:
            args = [{"doctype": self.get_doctype()}]

        if args and isinstance(args, (list, tuple)) and isinstance(args[0], dict):
            # doc = Product(dict(title="Product A"))
            args[0]["doctype"] = self.get_doctype()

        return super().__init__(*args, **kwargs)

    @classmethod
    def get_doctype(cls):
        global doctype_map
        _cls = cls
        while _cls not in doctype_map and _cls:
            _cls = _cls.__base__

        if not _cls:
            return None

        return doctype_map[_cls]

    @classmethod
    async def get_doc(cls, doc_id: str) -> Optional[T]:
        if await cls.exists(doc_id):
            return await asyncer.asyncify(frappe.get_doc)(cls.get_doctype(), doc_id)
        return None

    @classmethod
    async def get_all(cls,
                      filters: dict = None,
                      fields: List[str] = ["name"],
                      offset: int = 0,
                      count: int = 10,
                      order_by: str = None) -> List[T]:
        return await asyncer.asyncify(frappe.get_all)(
            cls.get_doctype(), filters=filters, fields=fields, limit_start=offset,
            limit_page_length=count, order_by=order_by)

    @classmethod
    async def db_set_value(cls, doc_id: str, fieldname: str, value):
        return await asyncer.asyncify(frappe.db.set_value)(
            cls.get_doctype(), doc_id, fieldname, value)

    @classmethod
    async def db_get_value(cls, doc_id: str, fieldname: str = "name", as_dict=None):
        return await asyncer.asyncify(frappe.db.get_value)(
            cls.get_doctype(), doc_id, fieldname, as_dict=as_dict
        )

    @classmethod
    def query(cls,
              query: str,
              values: Union[dict, tuple, list],
              as_dict: bool = True) -> Union[dict, list]:
        return frappe.db.sql(query, values, as_dict=as_dict)

    @classmethod
    def get_count(cls, filters: dict) -> int:
        return frappe.db.count(cls.get_doctype(), filters=filters)

    @classmethod
    async def exists(cls, doc_id: str):
        return await asyncer.asyncify(frappe.db.exists)(cls.get_doctype(), doc_id)

    async def reload(self) -> T:
        super().reload()
        return self

    # def __getattribute__(self, __name: str):
    #     # This is an attempt to make the Model compatible in both Sync & Async contexts
    #     # Right now, this causes db-connection racing condition issues
    #     # Could be looked into later
    #     attr = object.__getattribute__(self, __name)
    #     if not inspect.iscoroutinefunction(attr):
    #         return attr

    #     def _inner(*args, **kwargs):
    #         if args and args[0] == self:
    #             args = args[1:]
    #         try:
    #             _out = asyncio.create_task(attr(*args, **kwargs))
    #         except RuntimeError:
    #             _out = asyncer.runnify(attr)(*args, **kwargs)
    #         except BaseException:
    #             print("Err")

    #         return _out

    #     return _inner

    async def insert(self, ignore_permissions=None) -> T:
        if ignore_permissions is not None:
            self.flags.ignore_permissions = ignore_permissions

        self.set("__islocal", True)

        self.check_permission("create")
        self._set_defaults()
        self.set_user_and_timestamp()
        self.set_docstatus()
        self.check_if_latest()
        await self.run_method("before_insert")
        self._validate_links()
        # TODO: Update the event handlers inside to be async
        self.set_new_name()  # set_name=set_name, set_child_names=set_child_names
        self.set_parent_in_children()
        self.validate_higher_perm_levels()

        self.flags.in_insert = True
        await self.run_before_save_methods()
        self._validate()
        self.set_docstatus()
        self.flags.in_insert = False

        # parent
        if getattr(self.meta, "issingle", 0):
            await asyncer.asyncify(self.update_single)(self.get_valid_dict())
        else:
            try:
                await asyncer.asyncify(self.db_insert)()
            except frappe.DuplicateEntryError as e:
                # if not ignore_if_duplicate:
                raise e

        # children
        for d in self.get_all_children():
            await asyncer.asyncify(d.db_insert)()

        await self.run_method("after_insert")
        self.flags.in_insert = True

        # flag to prevent creation of event update log for create and update both
        # during document creation
        self.flags.update_log_for_doc_creation = True
        await self.run_post_save_methods()
        self.flags.in_insert = False

        # delete __islocal
        if hasattr(self, "__islocal"):
            delattr(self, "__islocal")

        # clear unsaved flag
        if hasattr(self, "__unsaved"):
            delattr(self, "__unsaved")

        return self

    async def save(self, ignore_permissions=None) -> T:
        if ignore_permissions is not None:
            self.flags.ignore_permissions = ignore_permissions

        if self.get("__islocal") or not self.get("name"):
            return await self.insert()

        self.check_permission("write", "save")

        self.set_user_and_timestamp()
        self.set_docstatus()
        self.check_if_latest()
        self.set_parent_in_children()
        self.set_name_in_children()

        self.validate_higher_perm_levels()
        self._validate_links()

        await self.run_before_save_methods()

        self._validate()
        self.set_docstatus()

        if self.meta.issingle:
            await asyncer.asyncify(self.update_single)(self.get_valid_dict())
        else:
            await asyncer.asyncify(self.db_update)()

        await asyncer.asyncify(self.update_children)()
        await self.run_post_save_methods()

        # clear unsaved flag
        if hasattr(self, "__unsaved"):
            delattr(self, "__unsaved")

        return self

    def update(self, d) -> T:
        super().update(d)
        return self

    async def delete(self, ignore_permissions=False) -> None:
        await asyncer.asyncify(super().delete)(ignore_permissions=ignore_permissions)
        return None

    async def run_before_save_methods(self):
        await asyncer.asyncify(self.load_doc_before_save)()
        await asyncer.asyncify(self.reset_seen)()

        # before_validate method should be executed before ignoring validations
        await self.run_method("before_validate")

        if self.flags.ignore_validate:
            return

        await self.run_method("validate")
        await self.run_method("before_save")

        self.set_title_field()

    async def run_post_save_methods(self):
        """Run standard methods after `INSERT` or `UPDATE`. Standard Methods are:

        - `on_update` for **Save**.
        - `on_update`, `on_submit` for **Submit**.
        - `on_cancel` for **Cancel**
        - `update_after_submit` for **Update after Submit**"""

        # doc_before_save = self.get_doc_before_save()

        await self.run_method("on_update")

        self.clear_cache()
        self.notify_update()

        # update_global_search(self)

        await asyncer.asyncify(self.save_version)()

        await self.run_method('on_change')

        if (self.doctype, self.name) in frappe.flags.currently_saving:
            frappe.flags.currently_saving.remove((self.doctype, self.name))

        self.latest = None

    def run_method(self, method, *args, **kwargs):
        """run standard triggers, plus those in hooks"""
        if "flags" in kwargs:
            del kwargs["flags"]

        if hasattr(self, method) and hasattr(getattr(self, method), "__call__"):
            fn = getattr(self, method)
        else:
            # hack! to run hooks even if method does not exist
            fn = lambda self, *args, **kwargs: None  # noqa

        hooked = FrappeModel.hook(fn, method=method)
        try:
            # Support both sync & async contexts
            _out = asyncio.create_task(hooked(self, *args, **kwargs))
        except RuntimeError:
            _out = asyncer.runnify(hooked)(self, *args, **kwargs)

        # self.run_notifications(method)

        return _out

    @staticmethod
    def hook(f, method):
        """Decorator: Make method `hookable` (i.e. extensible by another app).

        Note: If each hooked method returns a value (dict), then all returns are
        collated in one dict and returned. Ideally, don't return values in hookable
        methods, set properties in the document."""

        def add_to_return_value(self, new_return_value):
            if isinstance(new_return_value, dict):
                if not self.get("_return_value"):
                    self._return_value = {}
                self._return_value.update(new_return_value)
            else:
                self._return_value = new_return_value or self.get("_return_value")

        def _run_async_bound(self, fn):
            async def _inner(*args, **kwargs):
                if not getattr(fn, "__self__", None):
                    args = [self] + list(args)

                if inspect.iscoroutinefunction(fn):
                    return await fn(*args, **kwargs)
                else:
                    return fn(*args, **kwargs)

            return _inner

        def compose(fn, *hooks):
            async def runner(self, method, *args, **kwargs):
                add_to_return_value(self, await _run_async_bound(self, fn)(*args, **kwargs))

                for f in hooks:
                    add_to_return_value(
                        self,
                        await _run_async_bound(self, f)(method, *args, **kwargs))

                return self._return_value

            return runner

        def composer(self, *args, **kwargs):
            hooks = []

            doc_events = frappe.get_doc_hooks()
            for handler in doc_events.get(self.doctype, {}).get(method, []) \
                    + doc_events.get("*", {}).get(method, []):
                hooks.append(frappe.get_attr(handler))

            composed = compose(f, *hooks)
            return composed(self, method, *args, **kwargs)

        return composer
