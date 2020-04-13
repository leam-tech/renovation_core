// Copyright (c) 2020, LEAM Technology System and contributors
// For license information, please see license.txt

frappe.ui.form.on('Broadcast Message', {
    refresh: function (frm) {
        if (frm.doc.docstatus == 1) {
            frm.add_custom_button(__("Send Message"), () => {
                frappe.call({
                    method: "send",
                    doc: frm.doc
                });
            });
        }
    }
});
