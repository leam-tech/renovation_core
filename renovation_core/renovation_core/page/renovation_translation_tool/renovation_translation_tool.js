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
        this.wrapper.append(frappe.render_template('renovation_translation_tool'));
        frappe.utils.bind_actions_with_object(this.wrapper, this);
        this.setup_language_filter();
        this.fetch_doctypes()
    }

    fetch_doctypes() {
        frappe.call({
            module: "renovation_core.renovation_core",
            page: "renovation_translation_tool",
            method: "get_translatable_doctypes"
        }).then((res) => {
            this.doctypes = res.message.doctypes;
            this.setup_doctype_filter();
            this.docname_selector()
            this.docfield_selector()
        });
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
                this.selected_language = language_selector.get_value();
                this.load_translations()
            }
        });
    }

    setup_doctype_filter() {
        let doctype_selector = this.page.add_field({
            label: __("Document Type"),
            fieldname: 'selected_doctype',
            fieldtype: 'Select',
            options: this.doctypes,
            reqd: 1,
            change: () => {
                this.selected_doctype = doctype_selector.get_value()
                this.docfield_selector.$wrapper.find("select").empty()
                this.docname_selector.$wrapper.find("select").empty()
                this.body.empty();
                this.fetch_docnames()
                this.fetch_docfields()
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
                this.selected_docfield = this.docfield_selector.get_value()
                this.load_translations()
            }
        });
    }

    docname_selector() {
        this.docname_selector = this.page.add_field({
            label: __("Docname"),
            fieldname: 'selected_docname',
            fieldtype: 'Select',
            options: [],
            change: () => {
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
            }
        }).then((res) => {
            this.docfields = res.message.docfield;
            this.docfield_selector.$wrapper.find("select").add_options([{
                value: "",
                label: __("Select A Docfield") + "..."
            }].concat(res.message.docfields));
        });
    }

    fetch_docnames() {
        if (!this.selected_doctype) {
            return
        }
        // fetch docnames
        frappe.call({
            module: "renovation_core.renovation_core",
            page: "renovation_translation_tool",
            method: "get_translatable_docnames",
            args: {
                "doctype": this.selected_doctype
            }
        }).then((res) => {
            this.docfields = res.message.docfield;
            this.docname_selector.$wrapper.find("select").add_options([{
                value: "",
                label: __("Select A Docname") + "..."
            }].concat(res.message.docnames));
        });
    }

    render_translations() {
        this.body.empty();
        if (!this.translations_list.length) {
            this.set_empty_message(__("No translations found."));
        } else {
            this.show_translations_table(this.translations_list);
        }
        this.show_add_new_translation();
    }

    show_add_new_translation() {
        this.page.set_primary_action(
            __("Add A New Translation"),
            () => {

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
            .click(function () {

            });
    }

    add_edit_button(row, d) {
        $(`<button class='btn btn-success btn-xs'>${frappe.utils.icon('edit')}</button>`)
            .appendTo($(`<td class="pt-4">`).appendTo(row))
            .click(function () {

            });
    }

    load_translations() {
        // load translations
        if (this.selected_doctype && this.selected_docfield && this.selected_language) {
            frappe.call({
                module: "renovation_core.renovation_core",
                page: "renovation_translation_tool",
                method: "get_translations",
                args: {
                    "language": this.selected_language,
                    "doctype": this.selected_doctype,
                    "docname": this.selected_docname,
                    "docfield": this.selected_docfield
                }
            }).then((res) => {
                this.translations_list = res.message.translations;
                this.render_translations()
            });
        }
    }
}