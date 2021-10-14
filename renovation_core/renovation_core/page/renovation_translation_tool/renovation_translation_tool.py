import frappe

not_allowed_in_translation = ["DocType"]


@frappe.whitelist()
def get_doctypes():
    frappe.only_for("System Manager")
    doctypes = frappe.get_all("DocType",
                              filters={"name": ("not in", ",".join(not_allowed_in_translation))}, fields=["name"])
    doctypes_list = [{"label": frappe._(d.get("name")), "value": d.get("name")} for d in doctypes]
    return {
        "doctypes": sorted(doctypes_list, key=lambda d: d['label'])
    }
