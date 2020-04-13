// Copyright (c) 2018, Leam Technology Systems and contributors
// For license information, please see license.txt

frappe.ui.form.on('Renovation Report', {
	refresh: function (frm) {
		frm.add_custom_button(__("Add Default Filters"), frm.events.get_standard_filters)
	},
	get_standard_filters(frm) {
		if (typeof frm === "undefined")
			frm = cur_frm;
		if (!frm.doc.report) {
			frappe.message(__("Please Select Report"))
			return
		}
		frappe.call({
			method: "renovation_core.renovation_setup.doctype.renovation_report.renovation_report.get_defaults_filters",
			args: {
				report: frm.doc.report
			},
			freeze: true,
			callback: r => {
				if (r.xhr)
					return;
				if (r.message.is_standard) {
					frm.events.set_standard_filters(frm, r.message.script)
				}
				else {
					frappe.dom.eval(r.message.script || "");
					frappe.after_ajax(function () {
						frm.events.set_standard_filters(frm, frappe.query_reports[frm.doc.report]['filters'])
					})
				}
			}
		})
	},
	set_standard_filters(frm, filters) {
		frm.doc.filters = []
		filters.forEach(filter => {
			frm.add_child('filters', {
				"fieldname": filter['fieldname'],
				"fieldtype": filter['fieldtype'],
				"reqd": filter['reqd'],
				"options": filter['options'],
				"default_value": filter['default'],
				"label": filter['label']
			})
		})
		frm.refresh_field('filters')
	}
});
