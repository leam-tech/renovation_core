frappe.provide("frappe.treeview_settings")


frappe.treeview_settings['Renovation Sidebar'] = {
	fields: [
		{fieldname: "renovation_sidebar_name", fieldtype: "Data", reqd: 1, label: __("Title")},
		{fieldname: "tooltip", fieldtype: "Data", label: __("Tooltip")},
		{fieldname: "parent_renovation_sidebar", fieldtype: "Link", reqd: 1, options: "Renovation Sidebar", label: __("Parent Sidebar")},
		{fieldname: "is_group", fieldtype: "Check", label: __("Is Group")},
		{fieldname: "type", fieldtype: "Select", label: __("Type"), options:"\nForm\nReport\nPage\nLink"},
		{fieldname: "target_type", fieldtype: "Select", label: __("Target Type"), options:"\nDocType\nReport\nPage"},
		{fieldname: "target", fieldtype: "Dynamic Link", label: __("Target"), options: "target_type", depends_on:"eval:doc.type!=='Link'"},
		{fieldname: "link", fieldtype: "Data", label: __("Link"), depends_on:"eval:doc.type==='Link'"}
	]
}