import frappe

@frappe.whitelist(allow_guest=True)
def get_guest_token(guest_name=None, email=None, mobile_no=None):
  """
  Creates a `Guest Chat User` document instance to store the details of the Guest
  who is about to start with the admins. Providing the details are completely optional.
  :param guest_name: The name of the Guest
  :param email: The email of the Guest
  :param mobile_no: The mobile_no of the guest
  """
  from frappe.chat.website import token
  t = token()

  if guest_name:
    d = frappe.get_doc(frappe._dict(
      doctype="Guest Chat User",
      token=t,
      guest_name=guest_name,
      email=email,
      mobile_no=mobile_no
    )).insert(ignore_permissions=True)
  return t