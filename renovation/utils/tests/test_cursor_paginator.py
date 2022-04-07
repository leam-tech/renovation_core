from unittest import TestCase
from asyncer import runnify
from faker import Faker

import frappe  # Only used to make the fixtures
from renovation.utils.cursor_pagination import CursorPaginator


class TestCursorPaginator(TestCase):
    faker = Faker()
    user_fixtures = []

    @classmethod
    def setUpClass(cls) -> None:
        for i in range(50):
            cls.user_fixtures.append(frappe.get_doc(dict(
                doctype="User", send_welcome_email=0,
                first_name=cls.faker.first_name(),
                email=cls.faker.email(),
            )).insert())

    @classmethod
    def tearDownClass(cls) -> None:
        for user in cls.user_fixtures:
            user.delete()

    @runnify
    async def test_simple(self):
        _first = 10
        r = CursorPaginator("User")

        users = await r.execute({"first": _first})
        self.assertGreater(len(users), 0)

        self.assertIsNotNone(users.totalCount)
        self.assertIsNotNone(users.pageInfo)
        self.assertIsNotNone(users.edges)

        pageInfo = users.pageInfo
        self.assertIsNotNone(pageInfo.hasNextPage)
        self.assertIsNotNone(pageInfo.hasPreviousPage)
        self.assertIsNotNone(pageInfo.startCursor)
        self.assertIsNotNone(pageInfo.endCursor)

        self.assertEqual(len(users.edges), _first)
