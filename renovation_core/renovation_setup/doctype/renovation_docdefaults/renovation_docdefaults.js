// Copyright (c) 2018, Leam Technology Systems and contributors
// For license information, please see license.txt

frappe.ui.form.on('Renovation DocDefaults', {
	refresh: function(frm) {
		// hide Add Row button
		$('div[data-fieldname="fields"] button.grid-add-row').hide()
		
		frm.set_query("docfield", "fields", function(doc, cdt, cdn) {
			return {
				query: "renovation_core.renovation_setup.doctype.renovation_docdefaults.renovation_docdefaults.fieldname_query",
				filters: {
					dt: frm.doc.dt
				}
			}
		});
	},
	add_field: function(frm) {
		let d = new frappe.ui.Dialog({
			fields: [
				{
					'label': 'DocType',
					'fieldname': 'doctype',
					'fieldtype': 'Data',
					'read_only': true,
					'default': frm.doc.dt,
					'reqd': 1
				},
				{	// DocField
					'label': 'DocField',
					'fieldname': 'docfield', 
					'fieldtype': 'Link', 
					'options': 'DocField',
					'reqd': 1,
					'get_query': function() {
						return {
							query: "renovation_core.renovation_setup.doctype.renovation_docdefaults.renovation_docdefaults.fieldname_query",
							filters: {
								dt: frm.doc.dt
							}
						}
					}
				}
			],
			title: 'Add Field',
			primary_action: function() {
				d.hide();
				frappe.call({
					method: 'renovation_core.renovation_setup.doctype.renovation_docdefaults.renovation_docdefaults.get_docfield_info',
					args: {
						docfield_name: d.get_values().docfield
					},
					callback: (r) => {
						if (!r.exc && r.message) {
							r = r.message;
							var d = frappe.model.add_child(frm.doc, "Renovation DocDefault Items", "fields");
							d.fieldname = r.fieldname;
							d.fieldtype = r.fieldtype;
							d.label = r.label;
							if (d.fieldtype == "Link" || d.fieldtype == "Table")
								d.link_doctype = r.options;
							frm.refresh_field("fields");
						}
					}
				});
			}
		});
		d.show();
	},
	fetch_fields: function(frm) {

		return frappe.confirm(
			'This can clear your current fields. Continue ?',
			
			function(){
				return cur_frm.call({
					doc: cur_frm.doc,
					method: "fetch_fields",
					freeze: true,
					callback: function(r) {
						if(r.exc){
							frappe.msgprint("Field fetch failed. Pls try again");
						}
						console.log('Done')
					}
				});
			}
		)
	},
	fetch_mandatory_fields: function(frm) {

		return frappe.confirm(
			'This can clear your current fields. Continue ?',
			
			function(){
				return cur_frm.call({
					doc: cur_frm.doc,
					method: "fetch_mandatory_fields",
					freeze: true,
					callback: function(r) {
						if(r.exc){
							frappe.msgprint("Field fetch failed. Pls try again");
						}
						console.log('Done')
					}
				});
			}
		)
	}
});
