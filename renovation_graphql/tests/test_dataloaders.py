from unittest import TestCase
from asyncer import runnify
from faker import Faker

import frappe

from renovation_graphql.dataloaders import get_model_dataloader, get_child_table_dataloader


class TestDataLoaders(TestCase):
    fixture_users = []
    faker = Faker()

    @classmethod
    def setUpClass(cls):
        roles = [x.name for x in frappe.get_all(
            "Role", [["name", "NOT IN", ["All", "Guest"]]], limit_page_length=99)]

        for i in range(20):
            cls.fixture_users.append(frappe.get_doc(dict(
                doctype="User",
                first_name=cls.faker.first_name(),
                email=cls.faker.email(),
                send_welcome_email=0,
                roles=[
                    dict(role=x) for x in cls.faker.random.sample(roles, 5)
                ]
            )).insert())

    @classmethod
    def tearDownClass(cls) -> None:
        for user in cls.fixture_users:
            user.delete()

    @runnify
    async def test_model_dataloader(self):
        user_loader = get_model_dataloader("User")

        _user1 = self.fixture_users[0]
        _user2 = self.fixture_users[1]
        _user3 = self.fixture_users[2]

        user1_future = user_loader.load(_user1.name)
        user2_future = user_loader.load(_user2.name)
        userNonExistent_future = user_loader.load("random-non-existent-mister")
        user3_future = user_loader.load(_user3.name)

        user1 = await user1_future
        user2 = await user2_future
        user3 = await user3_future
        self.assertIsNone(await userNonExistent_future)

        for k in ("name", "first_name", "email"):
            self.assertEqual(user1.get(k), _user1.get(k))
            self.assertEqual(user2.get(k), _user2.get(k))
            self.assertEqual(user3.get(k), _user3.get(k))

    @runnify
    async def test_child_table_dataloader(self):
        role_loader = get_child_table_dataloader("Has Role", "User", "roles")

        _user1 = self.fixture_users[0]
        _user2 = self.fixture_users[1]
        _user3 = self.fixture_users[2]

        user1_future = role_loader.load(_user1.name)
        user2_future = role_loader.load(_user2.name)
        non_existent_future = role_loader.load("non-existent-random-user-1")
        user3_future = role_loader.load(_user3.name)

        user1_roles = await user1_future
        user2_roles = await user2_future
        user3_roles = await user3_future
        self.assertListEqual(await non_existent_future, [])

        self.assertListEqual(
            [x.role for x in _user1.roles],
            [x.role for x in user1_roles],
        )

        self.assertListEqual(
            [x.role for x in _user2.roles],
            [x.role for x in user2_roles],
        )

        self.assertListEqual(
            [x.role for x in _user3.roles],
            [x.role for x in user3_roles],
        )
