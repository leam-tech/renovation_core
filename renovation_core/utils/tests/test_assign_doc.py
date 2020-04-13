import frappe
from renovation_core.utils.json_generator import generate_json
from renovation_core.utils.test_runner import RenovationTestCase

from ..assign_doc import getDocsAssignedToUser, getUsersAssignedToDoc, unAssignDocFromUser


class TestAssign(RenovationTestCase):

  """
  We will try testing assigning between User and Blogger
  """

  def print_recorded_data(self):
    print(self.records_made)

  def test_getDocsAssignedToUser(self):
    assignment = self.get_test_records_assignments()[0]
    
    t = getDocsAssignedToUser(assignment[0])
    self.assertIsInstance(t, (list, tuple))
    
    t = [x for x in t if x.doctype == assignment[1] and x.docname == assignment[2]]
    self.assertGreater(len(t), 0)

  def test_getUsersAssignedToDoc(self):
    assignment = self.get_test_records_assignments()[0]
    
    t = getUsersAssignedToDoc(assignment[1], assignment[2])
    self.assertIsInstance(t, (list, tuple))
    
    t = [x for x in t if x.assignedTo == assignment[0]]
    self.assertGreater(len(t), 0)

  def test_unAssignDocFromUser(self):
    assignment = self.get_test_records_assignments()[0]
    
    unAssignDocFromUser(assignment[1], assignment[2], assignment[0])

    t = getDocsAssignedToUser(assignment[0])
    self.assertIsInstance(t, (list, tuple))
    
    t = [x for x in t if x.doctype == assignment[1] and x.docname == assignment[2]]
    self.assertEqual(len(t), 0)



  def get_test_records_assignments(self):
    assignments = []
    for todo in self.records_made[frappe.scrub("ToDo")]:
      assignments.append((todo.owner, todo.reference_type, todo.reference_name))
    
    return assignments

  def setUp(self):
    super(TestAssign, self).setUp()

  def tearDown(self):
    super(TestAssign, self).tearDown()

  def get_test_records(self):
    frappe.flags.in_import = True
    return frappe._dict(
        order=["User", "Blogger", "ToDo"],
        records=frappe._dict(
            user=get_user_test_docs(),
            blogger=get_blogger_test_docs(),
            todo=get_todo_test_docs()
        )
    )

def get_user_test_docs():
  d = generate_json([
      r"{{ repeat(5) }}",
      frappe._dict(
          doctype="User",
          first_name=r"{{ doc.firstName() }}",
          email=r"{{ doc.faker.email() }}",
          roles=[{
              "role": "System Manager"
          }]
      )
  ])

  return d

def get_blogger_test_docs():
  d = generate_json([
    r"{{ repeat(3) }}",
    frappe._dict(
      doctype="Blogger",
      _user=r"[unique:blogger_user]<<test_runner.get_filtered_single_data('user', {}, test_runner.faker.random_choices(elements=[0,1,2,3,4], length=1)[0])>>",
      user=r"<% if doc.get('_user') %><< doc.get('_user').get('name') >><% endif %>",
      short_name=r"<% if doc.get('_user') %> << doc.get('_user').get('first_name') >> <% endif %>",
      full_name=r"<% if doc.get('_user') %> << doc.get('_user').get('first_name') >> <% endif %>"
    )
  ])

  return d

def get_todo_test_docs():
  d = generate_json([
    r"{{ repeat(7) }}",
    frappe._dict(
      doctype="ToDo",
      owner=r"<<test_runner.records_made['user'][test_runner.faker.random_choices(elements=[0,1,2], length=1)[0]].get('name')>>",
      status='Open',
      date=r'{{ doc.faker.date() }}',
      priority=r'{{ doc.faker.random_choices(elements=["Low", "Medium", "High"], length=1)[0] }}',
      reference_type='Blogger',
      reference_name=r"<<test_runner.records_made['blogger'][test_runner.faker.random_choices(elements=[0,1,2], length=1)[0]].get('name')>>",
      description=r'{{ doc.faker.paragraph() }}'
    )
  ])
  return d