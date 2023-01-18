import asyncio
import inspect
from typing import List, TypeVar, Type

import frappe
import renovation
from renovation import RenovationModel
from renovation.native_model import FrappeDocType

T = TypeVar("T")


def _async(fn):
    def _inner(*args, **kwargs):
        return asyncio.run(fn(*args, **kwargs))

    return _inner


def _safe_async(fn):
    async def _inner(*args, **kwargs):
        if inspect.iscoroutinefunction(fn):
            return await fn(*args, **kwargs)
        else:
            return fn(*args, **kwargs)

    return _inner


class FrappeTestFixture():
    """
    A simple and responsible Fixture Manager for Frappe DocTypes
    :param DEFAULT_DOCTYPE: The doctype that will be used as default
    :param dependent_fixtures: A list of classes that will be used as dependent fixtures
    :param fixtures: A dict of already generated fixtures
    :param duplicate: A flag to indicate if the fixture is already set up
    """

    def __init__(self):
        self.DEFAULT_DOCTYPE = None
        self.TESTER_USER = str(renovation.user)
        self.dependent_fixtures = []
        self.fixtures = frappe._dict()
        self.duplicate = False

    def setUp(self, skip_fixtures=False, skip_dependencies=False):
        """
        Set up the fixtures. Fixture will not be duplicated if already set up.

        Args:
            skip_fixtures (bool): Skip the fixture creation
            skip_dependencies (bool): Skip the dependency creation

        Returns:
            None
        """

        if frappe.session.user != self.TESTER_USER:
            frappe.set_user(self.TESTER_USER)

        if self.isSetUp():
            self.duplicate = True
            og: FrappeTestFixture = self.get_locals_obj()[self.__class__.__name__]
            self.fixtures = getattr(og, "fixtures", renovation._dict())
            self._dependent_fixture_instances = getattr(
                og, "_dependent_fixture_instances", [])
            return
        if not skip_dependencies:
            self.make_dependencies()

        if not skip_fixtures:
            self.make_fixtures()
        self.get_locals_obj()[self.__class__.__name__] = self

    def make_dependencies(self):
        """
        Invokes setUp on dependent fixture classes
        """
        if not self.dependent_fixtures or not len(self.dependent_fixtures):
            return
        self._dependent_fixture_instances = []

        for d_class in self.dependent_fixtures:
            d = d_class()
            d.setUp()
            self._dependent_fixture_instances.append(d)

    def get_dependent_fixture_instance(self, doctype):
        if hasattr(
                self,
                "_dependent_fixture_instances") and isinstance(
                self._dependent_fixture_instances,
                list):
            dependent = list(
                filter(
                    lambda d: d.DEFAULT_DOCTYPE == doctype,
                    self._dependent_fixture_instances))
            return dependent[0] if dependent else None

    def destroy_dependencies(self):
        """
        Invokes tearDown on dependent fixture classes
        """
        if not self.dependent_fixtures or not len(self.dependent_fixtures):
            return

        # Reverse teardown

        for i in range(len(getattr(self, "_dependent_fixture_instances", []))):
            d = self._dependent_fixture_instances[len(
                self._dependent_fixture_instances) - i - 1]
            d.tearDown()

        self._dependent_fixture_instances = []

    def get_dependencies(self, doctype):
        """
        Get documents of specific doctype that this fixture depends on
        """
        if not self._dependent_fixture_instances:
            return []

        for d in self._dependent_fixture_instances:
            if doctype in d.fixtures:
                return d.fixtures[doctype]

        return []

    def make_fixtures(self):
        """
        Please override this function to make your own make_fixture implementation
        And call self.add_document to keep track of the created fixtures for cleaning up later
        """
        pass

    def delete_fixtures(self):
        """
        Goes through each fixture generated and deletes it
        """
        for dt, docs in self.fixtures.items():
            meta = frappe.get_meta(dt)
            for doc in docs:
                if not frappe.db.exists(dt, doc.name) or doc is None:
                    continue

                if type(doc) == FrappeDocType:
                    doc._doc.reload()
                else:
                    doc.reload()

                if doc.docstatus == 1:
                    doc.docstatus = 2
                    doc.save(ignore_permissions=True)

                frappe.delete_doc(
                    dt,
                    doc.name,
                    force=not meta.is_submittable,
                    ignore_permissions=True,
                    delete_permanently=True
                )

        self.fixtures = frappe._dict()

    def __getitem__(self, doctype_idx):
        if isinstance(doctype_idx, int):
            if not self.DEFAULT_DOCTYPE:
                raise Exception("DEFAULT_DOCTYPE is not defined")
            return self.fixtures[self.DEFAULT_DOCTYPE][doctype_idx]

        return self.fixtures[doctype_idx]

    def __len__(self):
        if not self.DEFAULT_DOCTYPE:
            raise Exception("DEFAULT_DOCTYPE is not defined")

        return len(self.fixtures.get(self.DEFAULT_DOCTYPE, []))

    def tearDown(self):
        """
        Tear Down all generated fixtures
        """
        if frappe.session.user != self.TESTER_USER:
            frappe.set_user(self.TESTER_USER)

        if self.duplicate:
            self.fixtures = frappe._dict()
            self._dependent_fixture_instances = []
            self.duplicate = False
            return
        self.delete_fixtures()
        self.destroy_dependencies()
        self.get_locals_obj()[self.__class__.__name__] = None

    def add_document(self, doc):
        """
        Call this after creation of every fixture to keep track of it for deletion later
        """
        if doc.doctype not in self.fixtures:
            self.fixtures[doc.doctype] = []

        self.fixtures[doc.doctype].append(doc)

    def isSetUp(self):
        """
        Checks if another instance of the same fixture class is already set up
        """
        class_name = self.__class__.__name__
        return not not self.get_locals_obj().get(class_name, 0)

    def get_locals_obj(self):
        if "test_fixtures" not in frappe.flags:
            frappe.flags.test_fixtures = frappe._dict()

        return frappe.flags.test_fixtures


class RenovationTestFixture(FrappeTestFixture):
    """
    A simple and responsible Fixture Manager for Renovation Models
    :param DEFAULT_MODEL: The model that will be used as default
    :param dependent_fixtures: A list of classes that will be used as dependent fixtures
    :param fixtures: A dict of already generated fixtures
    :param duplicate: A flag to indicate if the fixture is already set up
    """

    def __init__(self):
        self.DEFAULT_MODEL: RenovationModel = None
        self.TESTER_USER = str(renovation.user)
        self.dependent_fixtures = []
        self.fixtures = renovation._dict()
        self.duplicate = False

    async def setUp(self, skip_fixtures=False, skip_dependencies=False):
        """
        Set up the fixtures. Fixture will not be duplicated if already set up.

        Args:
            skip_fixtures (bool): Skip the fixture creation
            skip_dependencies (bool): Skip the dependency creation

        Returns:
            None
        """

        if renovation.user != self.TESTER_USER:
            renovation.set_user(self.TESTER_USER)

        if self.isSetUp():
            self.duplicate = True
            og: FrappeTestFixture = self.get_locals_obj()[self.__class__.__name__]
            self.fixtures = getattr(og, "fixtures", renovation._dict())
            self._dependent_fixture_instances = getattr(
                og, "_dependent_fixture_instances", [])
            return
        if not skip_dependencies:
            await self.make_dependencies()

        if not skip_fixtures:
            await self.make_fixtures()
        self.get_locals_obj()[self.__class__.__name__] = self

    async def make_dependencies(self):
        """
        Invokes setUp on dependent fixture classes
        """
        if not self.dependent_fixtures or not len(self.dependent_fixtures):
            return
        self._dependent_fixture_instances = []

        for d_class in self.dependent_fixtures:
            d = d_class()
            await (_safe_async(d.setUp))()
            self._dependent_fixture_instances.append(d)

    def get_dependent_fixture_instance(self, model: Type[RenovationModel]):
        if hasattr(
                self,
                "_dependent_fixture_instances") and isinstance(
                self._dependent_fixture_instances,
                list):
            dependent = list(
                filter(
                    lambda d: d.DEFAULT_MODEL == model,
                    self._dependent_fixture_instances))
            return dependent[0] if dependent else None

    async def destroy_dependencies(self):
        """
        Invokes tearDown on dependent fixture classes
        """
        if not self.dependent_fixtures or not len(self.dependent_fixtures):
            return

        # Reverse teardown

        for i in range(len(getattr(self, "_dependent_fixture_instances", []))):
            d = self._dependent_fixture_instances[len(
                self._dependent_fixture_instances) - i - 1]
            await _safe_async(d.tearDown)()

        self._dependent_fixture_instances = []

    def get_dependencies(self, model: T) -> List[T]:
        """
        Get documents of specific model that this fixture depends on
        """
        if not self._dependent_fixture_instances:
            return []

        for d in self._dependent_fixture_instances:
            if model in d.fixtures:
                return d.fixtures[model]

        return []

    async def make_fixtures(self):
        """
        Please override this function to make your own make_fixture implementation
        And call self.add_document to keep track of the created fixtures for cleaning up later
        """
        pass

    async def delete_fixtures(self):
        """
        Goes through each fixture generated and deletes it
        """
        for model, docs in self.fixtures.items():
            _docs = list(docs)
            _docs.reverse()
            for doc in _docs:
                if not await model.exists(doc.name) or doc is None:
                    continue

                await doc.reload()
                if doc.docstatus == 1:
                    doc.docstatus = 2
                    await doc.save(ignore_permissions=True)

                await doc.delete(ignore_permissions=True)

        self.fixtures = renovation._dict()

    def __getitem__(self, doctype_idx):
        if isinstance(doctype_idx, int):
            if not self.DEFAULT_MODEL:
                raise Exception("DEFAULT_MODEL is not defined")
            return self.fixtures[self.DEFAULT_MODEL][doctype_idx]

        return self.fixtures[doctype_idx]

    def __len__(self):
        if not self.DEFAULT_MODEL:
            raise Exception("DEFAULT_MODEL is not defined")

        return len(self.fixtures.get(self.DEFAULT_MODEL, []))

    async def tearDown(self):
        """
        Tear Down all generated fixtures
        """
        if renovation.user != self.TESTER_USER:
            renovation.set_user(self.TESTER_USER)

        if self.duplicate:
            self.fixtures = renovation._dict()
            self._dependent_fixture_instances = []
            self.duplicate = False
            return
        await self.delete_fixtures()
        await self.destroy_dependencies()
        self.get_locals_obj()[self.__class__.__name__] = None

    def add_document(self, doc, model: RenovationModel = None):
        """
        Call this after creation of every fixture to keep track of it for deletion later
        """
        if not model:
            model = self.DEFAULT_MODEL
        if model not in self.fixtures:
            self.fixtures[model] = []

        self.fixtures[model].append(doc)

    def isSetUp(self):
        """
        Checks if another instance of the same fixture class is already set up
        """
        class_name = self.__class__.__name__
        return not not self.get_locals_obj().get(class_name, 0)

    def get_locals_obj(self):
        if "test_fixtures" not in frappe.flags:
            frappe.flags.test_fixtures = renovation._dict()

        return frappe.flags.test_fixtures
