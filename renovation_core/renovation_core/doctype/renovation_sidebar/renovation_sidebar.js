// Copyright (c) 2019, LEAM Technology System and contributors
// For license information, please see license.txt

frappe.ui.form.on('Renovation Sidebar', {
	// setup: function(frm) {
	// 	frm.toggle_reqd('parent_renovation_sidebar', frm.doc.name !=="All Renovation Sidebar")
	// 	frm.set_query('sidebar_group', 'include_from', function(doc, cdt, cdn){
	// 		return {
	// 			"filters": {
	// 				"is_group": 1
	// 			}
	// 		}
	// 	})
	// },
	// refresh: function (frm) {
	// 	frm.events.set_target_options(frm)
	// },
	// set_target_options: function (frm) {
	// 	if (frm.doc.type !== "Link") {
	// 		let option = frm.doc.type === "Form" ? "DocType" : frm.doc.type
	// 		frm.set_value('target_type', option)
	// 	}
	// },
	// type: function (frm) {
	// 	frm.events.set_target_options(frm)
	// }
});