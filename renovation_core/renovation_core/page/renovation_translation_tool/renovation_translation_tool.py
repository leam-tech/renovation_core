import frappe

not_allowed_in_translation = ["DocType"]


@frappe.whitelist()
def get_translatable_doctypes():
    __check_read_renovation_translation_tool_perm()
    doctypes = frappe.get_all("DocType",
                              filters={"name": ("not in", ",".join(not_allowed_in_translation))}, fields=["name"])
    doctypes_list = [{"label": frappe._(d.get("name")), "value": d.get("name")} for d in doctypes]
    return {
        "doctypes": sorted(doctypes_list, key=lambda d: d['label'])
    }


def __check_read_renovation_translation_tool_perm():
    doc = frappe.get_doc("Page", "renovation_translation_tool")
    if not doc.is_permitted():
        frappe.throw(
            frappe._("You don't have access to page Renovation Translation Tool."),
            frappe.PermissionError,
        )


@frappe.whitelist()
def get_translatable_docfields(doctype):
    __check_read_renovation_translation_tool_perm()
    doctype_meta = frappe.get_meta(doctype)
    translatable_docfields = doctype_meta.get_translatable_fields()
    translatable_docfields_list = [{"label": frappe._(d), "value": d} for d in translatable_docfields]
    return {
        "docfields": sorted(translatable_docfields_list, key=lambda d: d['label'])
    }
