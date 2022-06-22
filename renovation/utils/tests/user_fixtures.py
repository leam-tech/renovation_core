from typing import List
from faker import Faker

import frappe
from renovation.tests import FrappeTestFixture


class UserFixtures(FrappeTestFixture):
    faker = Faker()

    def __init__(self):
        super().__init__()
        self.DEFAULT_DOCTYPE = "User"

    def make_fixtures(self):
        self.fixtures[self.DEFAULT_DOCTYPE] = []

    def get_user_with_role(
            self,
            should_have_roles: List[str] = [],
            should_not_have_roles: List[str] = []) -> dict:
        """
        Returns a User Document
        who has all the roles as per the criteria specified.

        It will create a new User who conforms to the criteria if one is not found
        """
        should_have_roles: set = set(should_have_roles or [])
        should_not_have_roles: set = set(should_not_have_roles or [])

        for user in self:
            roles = set(x.role for x in user.roles)
            if roles != should_have_roles:
                continue

            if len(should_not_have_roles.intersection(roles)) > 0:
                continue

            return user

        # We did not find a User that satisfied the condition.
        # Let's make new User that conforms
        user = frappe.get_doc(dict(
            doctype="User",
            first_name=self.faker.first_name(),
            last_name=self.faker.last_name(),
            email=self.faker.email(),
            send_welcome_email=0,
        ))
        for role in should_have_roles:
            user.append("roles", dict(role=role))

        user.insert(ignore_permissions=True)
        self.add_document(user)

        return user
