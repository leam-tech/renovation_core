// Copyright (c) 2018, Leam Technology Systems and contributors
// For license information, please see license.txt

frappe.ui.form.on('Renovation DocField', {
	setup: function(frm) {
		frm.set_query('p_doctype', function(doc) {
			var filters = [];
			if(frappe.session.user!=="Administrator") {
				filters.push(['DocType', 'module', 'not in', ['Core', 'Custom']])
			}
			return {
				"filters": filters
			}
		});
	},
	p_doctype: function(frm) {
		if(!frm.doc.p_doctype) {
			set_field_options('fieldname', '');
			return;
		}
		var fieldname = frm.doc.fieldname || null;
		return frappe.call({
			method: 'renovation_core.renovation_core.doctype.renovation_docfield.renovation_docfield.get_fields_label',
			args: { doctype: frm.doc.p_doctype, fieldname: frm.doc.fieldname },
			callback: function(r, rt) {
				set_field_options('fieldname', r.message);
				var fieldnames = $.map(r.message, function(v) { return v.value; });

				if(fieldname==null || !in_list(fieldnames, fieldname)) {
					fieldname = fieldnames[-1];
				}

				frm.set_value('fieldname', fieldname);
			}
		});
	},
	refresh: function(frm) {
		frm.toggle_enable('p_doctype', frm.doc.__islocal);
		frm.trigger('p_doctype');
		frm.toggle_reqd('label', !frm.doc.fieldname);
	}
});
