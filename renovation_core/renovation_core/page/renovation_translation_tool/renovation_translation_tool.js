frappe.pages['renovation_translation_tool'].on_page_load = function (wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Renovation Translation Tool',
        single_column: true,
        card_layout: true,
    });
    $("<div class='renovation-translations' style='min-height: 200px; padding: 15px;'></div>").appendTo(page.main);
    $(frappe.render_template("renovation_translation_tool_help", {})).appendTo(page.main);
    frappe.renovation_translation_tool = new RenovationTranslationTool(page);
}

class RenovationTranslationTool {
    constructor(page) {
        this.page = page;
        this.wrapper = $(page.body);
        this.body = $(this.wrapper).find(".renovation-translations");
        this.setup_language_filter();
        this.setup_renovation_translation_tool_filter_fields()
    }

    setup_renovation_translation_tool_filter_fields() {
        this.docfields = []
        this.setup_doctype_filter();
        this.docname_selector()
        this.docfield_selector()

    }

    setup_language_filter() {
        let languages = Object.keys(frappe.boot.lang_dict).map(language_label => {
            let value = frappe.boot.lang_dict[language_label];
            return {
                label: `${language_label} (${value})`,
                value: value
            };
        });

        let language_selector = this.page.add_field({
            label: __("Select Language"),
            fieldname: 'selected_language',
            fieldtype: 'Select',
            options: languages,
            reqd: 1,
            change: () => {
                if (!language_selector.get_value() || (this.selected_language === language_selector.get_value())) {
                    return
                }
                this.selected_language = language_selector.get_value();
                this.load_translations()
            }
        });
    }

    setup_doctype_filter() {
        let doctype_selector = this.page.add_field({
            label: __("Document Type"),
            fieldname: 'selected_doctype',
            fieldtype: 'Link',
            options: "DocType",
            reqd: 1,
            change: () => {
                if (!doctype_selector.get_value() || (this.selected_doctype === doctype_selector.get_value())) {
                    return
                }
                this.selected_doctype = doctype_selector.get_value()
                this.docfield_selector.$wrapper.find("select").empty()
                this.docname_selector.set_input("")
                this.docname_selector.df.read_only = frappe.model.is_single(this.selected_doctype) ? 1 : 0
                this.docname_selector.refresh()
                this.body.empty();
                this.selected_docname = ""
                this.selected_docfield = ""
                this.fetch_docfields()
                this.load_translations()
            }
        });

    }

    docfield_selector() {
        this.docfield_selector = this.page.add_field({
            label: __("Translatable Docfield"),
            fieldname: 'selected_docfield',
            fieldtype: 'Select',
            options: [],
            change: () => {
                if (this.selected_docfield === this.docfield_selector.get_value()) {
                    return
                }
                this.selected_docfield = this.docfield_selector.get_value()
                this.load_translations()
            }
        });
    }

    docname_selector() {
        this.docname_selector = this.page.add_field({
            label: __("Docname"),
            fieldname: 'selected_docname',
            fieldtype: 'Dynamic Link',
            options: "selected_doctype",
            read_only: 1,
            change: () => {
                if (this.selected_docname === this.docname_selector.get_value()) {
                    return
                }
                this.selected_docname = this.docname_selector.get_value()
                this.load_translations()
            }
        });
    }

    fetch_docfields() {
        if (!this.selected_doctype) {
            return
        }
        // fetch translatable docfields
        frappe.call({
            module: "renovation_core.renovation_core",
            page: "renovation_translation_tool",
            method: "get_translatable_docfields",
            args: {
                "doctype": this.selected_doctype
            },
            freeze: true
        }).then((res) => {
            this.docfields = res.message.docfields;
            this.docfield_selector.$wrapper.find("select").add_options([{
                value: "",
                label: __("Select A Docfield") + "..."
            }].concat(res.message.docfields));
        });
    }

    render_translations() {
        this.body.empty();
        if (!this.translations_list.length) {
            this.set_empty_message(__("No translations found."));
        } else {
            this.show_translations_table(this.translations_list);
        }
        if (!this.translation_btn_added) {
            this.show_add_new_translation();
        }

    }

    get_value_for_translation(doctype, docname, docfield) {
        return frappe.call({
            method: "renovation_core.renovation_core.page.renovation_translation_tool.renovation_translation_tool.get_value_from_doc_for_translation",
            type: 'GET',
            args: {
                doctype: doctype,
                docname: docname,
                docfield: docfield
            }
        });
    }

    show_add_new_translation() {
        this.translation_btn_added = true
        /**
         We need the following to add a translation with context
         key:doctype:name:fieldname
         key:doctype:name
         key:parenttype:parent
         key:doctype:fieldname
         key:doctype
         key:parenttype
         */
        this.page.set_primary_action(
            __("Add A New Translation"),
            async () => {
                let latest_translation = this.translations_list.filter(df => df.name === this.translation_edit_name)[0]
                const doctype_is_single = frappe.model.is_single(this.selected_doctype)
                const selected_docname = doctype_is_single ? this.selected_doctype : this.translation_edit_name ? latest_translation.docname : this.selected_docname
                const selected_docfield = this.translation_edit_name ? latest_translation.docfield : this.selected_docfield

                if (!this.translation_edit_name && selected_docname && this.selected_doctype && selected_docfield) {
                    const check_translations = (this.translations_list || []).filter(tr => tr.context === `${this.selected_doctype}:${selected_docname}:${selected_docfield}`)
                    if (check_translations.length) {
                        latest_translation = check_translations[0]
                    } else {
                        // lets fetch the latest value/source text from db so user can translate
                        const response = await this.get_value_for_translation(this.selected_doctype, selected_docname, selected_docfield)
                        latest_translation = {}
                        latest_translation.value = response.message[selected_docfield];
                        latest_translation.source_text = latest_translation.value
                        latest_translation.context = `${this.selected_doctype}:${selected_docname}:${selected_docfield}`
                    }

                }
                const default_value = latest_translation ? latest_translation.value : null
                const default_source_text = latest_translation ? latest_translation.source_text : null
                const default_translated_text = latest_translation ? latest_translation.translated_text : null
                let default_context = latest_translation ? latest_translation.context : this.selected_doctype
                if (!latest_translation) {
                    if (selected_docname) {
                        default_context += `:${selected_docname}`
                    }
                    if (selected_docfield) {
                        default_context += `:${selected_docfield}`
                    }
                }
                let default_fields = [
                    {
                        fieldtype: "Data",
                        label: __("Language"),
                        reqd: 1,
                        read_only: 1,
                        fieldname: "language",
                        default: this.selected_language
                    },
                    {
                        fieldtype: "Data",
                        label: __("Document Type"),
                        reqd: 1,
                        read_only: 1,
                        fieldname: "doctype",
                        default: this.selected_doctype
                    },
                    {
                        fieldtype: "Data",
                        label: __("Docname"),
                        reqd: 1,
                        read_only: 1,
                        fieldname: "docname",
                        default: selected_docname
                    },
                    {
                        fieldtype: "Data",
                        label: __("Docfield"),
                        reqd: 1,
                        read_only: 1,
                        fieldname: "docfield",
                        default: selected_docfield
                    },
                    {
                        fieldtype: "Code",
                        label: __("Value"),
                        reqd: 1,
                        read_only: 1,
                        fieldname: "value",
                        default: default_value
                    },
                    {
                        fieldtype: "Code",
                        label: __("Source Text"),
                        reqd: 1,
                        read_only: 1,
                        fieldname: "source_text",
                        default: default_source_text,
                        description: ""
                    },
                    {
                        fieldtype: "Code",
                        label: __("Translated Text"),
                        reqd: 1,
                        read_only: 0,
                        fieldname: "translated_text",
                        default: default_translated_text
                    },
                    {
                        fieldtype: "Data",
                        label: __("Context"),
                        reqd: 1,
                        read_only: 1,
                        fieldname: "context",
                        default: default_context
                    },
                ]
                const set_field_readable = (fieldname) => {
                    let field = default_fields.find((df) => df.fieldname === fieldname)
                    field.read_only = 0
                }
                if (!selected_docfield) {
                    default_fields = default_fields.filter((df) => df.fieldname !== "docfield")
                    default_fields = default_fields.filter((df) => df.fieldname !== "value")
                    if (!this.translation_edit_name) {
                        set_field_readable("source_text")
                    }
                }
                if (!selected_docname) {
                    default_fields = default_fields.filter((df) => df.fieldname !== "value")
                    default_fields = default_fields.filter((df) => df.fieldname !== "docname")
                    if (!this.translation_edit_name) {
                        set_field_readable("source_text")
                    }
                }
                if (selected_docfield && !this.translation_edit_name) {
                    let field = default_fields.find((df) => df.fieldname === 'source_text')
                    field.read_only = 0
                    if (selected_docfield && selected_docname) {
                        field.description = __("Can be set to wildcard (*) for second order of precedence. Please read documentation below for further clarifications.")
                    }
                }
                const dialog_title = this.translation_edit_name ? __("Edit translation") : __("Add New Translation")
                let d = new frappe.ui.Dialog({
                    title: dialog_title,
                    fields: default_fields
                });
                d.set_primary_action(__('Save'), () => {
                    /**
                     language,
                     source_text,
                     translated_text,
                     context=None,
                     doctype=None,
                     docname=None,
                     docfield=None
                     */
                    let args = d.get_values();
                    if (!args) {
                        return;
                    }
                    if (!this.translation_edit_name) {
                        frappe.call({
                            method: "renovation_core.utils.translate.add_translation",
                            args: args,
                            freeze: true,
                            callback: (r) => {
                                if (r.exc) {
                                    frappe.msgprint(__("Did not add translation. Please try again!"));
                                } else {
                                    this.load_translations();
                                }
                            }
                        });
                    } else {
                        // simple edit ie change translated value..
                        frappe.call({
                            method: "frappe.client.set_value",
                            args: {
                                doctype: "Translation",
                                name: this.translation_edit_name,
                                fieldname: "translated_text",
                                value: args.translated_text
                            },
                            callback: (r) => {
                                if (r.exc) {
                                    frappe.msgprint(__("Did not edit translation. Please try again!"));
                                } else {
                                    this.load_translations();
                                }
                            }
                        })
                    }
                    d.hide();
                });
                d.show();
                d.onhide = () => {
                    this.translation_edit_name = null
                };
            },
            "small-add"
        );
    }

    set_empty_message(message) {
        this.body.html(`
		<div class="text-muted flex justify-center align-center" style="min-height: 300px;">
			<p class='text-muted'>
				${message}
			</p>
		</div>`);
    }

    show_translations_table(translation_list) {
        this.table = $("<div class='table-responsive'>\
			<table class='table table-borderless'>\
				<thead><tr></tr></thead>\
				<tbody></tbody>\
			</table>\
		</div>").appendTo(this.body);

        const table_columns = [
            [__("Document Type"), 150],
            [__("Docname"), 150],
            [__("Docfield"), 150],
            [__("Value"), 150],
            [__("Source Text"), 150],
            [__("Translated Text"), 150],
            [__("Context"), 150],
            ["", 40]
        ];

        table_columns.forEach((col) => {
            $("<th>")
                .html(col[0])
                .css("width", col[1] + "px")
                .appendTo(this.table.find("thead tr"));
        });

        translation_list.forEach((d) => {

            let row = $("<tr>").appendTo(this.table.find("tbody"));
            this.add_cell(row, d, "document_type");
            this.add_cell(row, d, "docname");
            this.add_cell(row, d, "docfield");
            this.add_cell(row, d, "value");
            this.add_cell(row, d, "source_text");
            this.add_cell(row, d, "translated_text");
            this.add_cell(row, d, "context")

            // buttons
            this.add_edit_button(row, d);
            this.add_delete_button(row, d);
        });
    }

    add_cell(row, d, fieldname) {
        return $("<td>").appendTo(row)
            .attr("data-fieldname", fieldname)
            .addClass("pt-4")
            .html(__(d[fieldname]));
    }

    add_delete_button(row, d) {
        $(`<button class='btn btn-danger btn-xs'>${frappe.utils.icon('delete')}</button>`)
            .appendTo($(`<td class="pt-4">`).appendTo(row))
            .click(() => {
                frappe.confirm(__("Confirm delete translation?"), () => {
                    frappe.call({
                        freeze: true,
                        method: "frappe.client.delete",
                        args: {
                            doctype: "Translation",
                            name: d.name,
                        },
                        callback: (r) => {
                            if (r.exc) {
                                frappe.msgprint(__("Did not delete translation. Please try again!"));
                            } else {
                                this.load_translations();
                            }
                        }
                    })
                })
            });
    }

    add_edit_button(row, d) {
        $(`<button class='btn btn-success btn-xs'>${frappe.utils.icon('edit')}</button>`)
            .appendTo($(`<td class="pt-4">`).appendTo(row))
            .click(() => {
                this.translation_edit_name = d.name
                this.page.btn_primary.trigger("click")
            });
    }

    load_translations() {
        // load translations
        if (this.selected_doctype && this.selected_language) {
            frappe.call({
                module: "renovation_core.renovation_core",
                page: "renovation_translation_tool",
                method: "get_translations",
                args: {
                    "language": this.selected_language,
                    "doctype": this.selected_doctype,
                    "docname": this.selected_docname,
                    "docfield": this.selected_docfield
                },
                freeze: true
            }).then((res) => {
                this.translations_list = res.message.translations;
                this.render_translations()
            });
        }
    }
}