import frappe
from frappe.api import validate_auth
from frappe.utils import cint


@frappe.whitelist(allow_guest=True)
def get_user_info(token=None, sid=None):
    if token:
        # Bearer Token
        validate_auth()
    current_user = frappe.session.user
    data = {
        'user': current_user,
        'sid': frappe.session.sid if not token else current_user
    }

    if data["user"] == "Guest":
        # check if guests are allowed
        data["allow_guest"] = cint(frappe.db.get_value(
            "System Settings", None, "socketio_allow_guest") or 0)

    return data
