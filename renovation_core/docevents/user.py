import frappe


def on_trash(doc, method=None):
    for token in frappe.get_all("OAuth Bearer Token", {"user": doc.name}):
        frappe.delete_doc("OAuth Bearer Token", token.name)
