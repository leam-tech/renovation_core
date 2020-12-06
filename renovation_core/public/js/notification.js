frappe.ui.form.on('Notification', {
  refresh: function(frm) {
    frm.events.setup_sms_field_name_select(frm)
  },
	document_type: function(frm) {
		frm.events.setup_sms_field_name_select(frm);
	},
  setup_sms_field_name_select: function(frm) {
		// get the doctype to update fields
		if (!frm.doc.document_type) {
			return;
		}

		frappe.model.with_doctype(frm.doc.document_type, function() {
			let get_select_options = function(df, parent_field) {
				let select_value = parent_field ? df.fieldname + ',' + parent_field : df.fieldname;
				return {
					value: select_value,
					label: df.fieldname + ' (' + __(df.label) + ')'
				};
			};
			let fields = frappe.get_doc('DocType', frm.doc.document_type).fields;
      let receiver_fields = [];
      if (in_list(['WhatsApp', 'SMS'], frm.doc.channel)) {
				receiver_fields = $.map(fields, function(d) {
					return d.options == 'Phone' || d.options == 'Mobile' ? get_select_options(d) : null;
				});
			}

			frappe.meta.get_docfield(
				'SMS Recipient',
				'field_name',
				frm.doc.name
			).options = [''].concat(receiver_fields);

			frm.fields_dict.sms_recipients.grid.refresh();
		});
	}
})