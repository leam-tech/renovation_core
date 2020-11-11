"use strict";

frappe.ui.form.on('Notification', {
  refresh: function refresh(frm) {
    frm.events.setup_sms_field_name_select(frm);
  },
  document_type: function document_type(frm) {
    frm.events.setup_sms_field_name_select(frm);
  },
  setup_sms_field_name_select: function setup_sms_field_name_select(frm) {
    // get the doctype to update fields
    if (!frm.doc.document_type) {
      return;
    }

    frappe.model.with_doctype(frm.doc.document_type, function () {
      var get_select_options = function get_select_options(df, parent_field) {
        var select_value = parent_field ? df.fieldname + ',' + parent_field : df.fieldname;
        return {
          value: select_value,
          label: df.fieldname + ' (' + __(df.label) + ')'
        };
      };

      var fields = frappe.get_doc('DocType', frm.doc.document_type).fields;
      var receiver_fields = [];

      if (in_list(['WhatsApp', 'SMS'], frm.doc.channel)) {
        receiver_fields = $.map(fields, function (d) {
          return d.options == 'Phone' || d.options == 'Mobile' ? get_select_options(d) : null;
        });
      }

      frappe.meta.get_docfield('SMS Recipient', 'field_name', frm.doc.name).options = [''].concat(receiver_fields);
      frm.fields_dict.sms_recipients.grid.refresh();
    });
  }
});