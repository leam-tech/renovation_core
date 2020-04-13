import frappe


@frappe.whitelist()
def getDocsAssignedToUser(user=frappe.session.user, status="Open", doctype=None):

  filters = {
      "owner": user,
      "status": status
  }
  if doctype:
    filters["reference_type"] = doctype

  todos = frappe.get_list("ToDo", fields=[
      "date as dueDate",
      "status",
      "assigned_by as assignedBy",
      "assigned_by_full_name as assignedByFullName",
      "owner as assignedTo",
      "priority",
      "description",
      "reference_type as doctype",
      "reference_name as docname"
  ], filters=filters)

  for td in todos:
    # get assignedToFullName
    td[u"assignedToFullName"] = frappe.get_value(
        "User", td.assignedTo, "full_name")

  return todos


@frappe.whitelist()
def getUsersAssignedToDoc(doctype, name, status="Open"):

  filters = {
      "reference_type": doctype,
      "reference_name": name,
      "status": status
  }

  todos = frappe.get_list("ToDo", fields=[
      "date as dueDate",
      "status",
      "assigned_by as assignedBy",
      "assigned_by_full_name as assignedByFullName",
      "owner as assignedTo",
      "priority",
      "description"
  ], filters=filters)

  for td in todos:
    # get assignedToFullName
    td[u"assignedToFullName"] = frappe.get_value(
        "User", td.assignedTo, "full_name")

  return todos


@frappe.whitelist()
def unAssignDocFromUser(doctype, docname, user=frappe.session.user):
  # get Open todo and delete
  todo = frappe.get_value("ToDo", filters={
      "owner": user,
      "reference_type": doctype,
      "reference_name": docname,
      "status": "Open"
  })

  if not todo:
    frappe.throw("User {} is not assigned to {} {}".format(
        user, doctype, docname))
  frappe.delete_doc("ToDo", todo)

  return "OK"
