// Copyright (c) 2018, Leam Technology Systems and contributors
// For license information, please see license.txt

frappe.ui.form.on('Renovation Image Settings', {
	refresh: function(frm) {
		frm.add_custom_button(__('Regenerate All'), function() {
			frappe.confirm('Re applying watermarks and generating thumbnails for them is a long process. Are you sure to proceed ?', function() {
				frappe.call({
					method: 'reapply_all',
					doc: frm.doc
				})
			})
		})
	}
});
