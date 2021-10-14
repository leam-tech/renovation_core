frappe.pages['renovation_translation_tool'].on_page_load = function (wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Renovation Translation Tool',
        single_column: true,
        card_layout: true,
    });

    frappe.renovation_translation_tool = new RenovationTranslationTool(page);
}

class RenovationTranslationTool {
    constructor(page) {
        this.page = page;
        this.wrapper = $(page.body);
        this.wrapper.append(frappe.render_template('renovation_translation_tool'));
        frappe.utils.bind_actions_with_object(this.wrapper, this);
        this.setup_language_filter();
        this.fetch_doctypes()
    }

    fetch_doctypes() {
        frappe.call({
            module: "renovation_core.renovation_core",
            page: "renovation_translation_tool",
            method: "get_doctypes"
        }).then((res) => {
            this.doctypes = res.message.doctypes;
            this.setup_doctype_filter();
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
            reqd: 1,
            change: () => {
                this.selected_docfield = this.docfield_selector.get_value()
                this.load_translations()
            }
        });
    }

    fetch_docfields() {
        // fetch translatable docfields
    }

    load_translations() {
        // load translations
        if (this.selected_doctype && this.selected_docfield && this.selected_language) {
            
        }
    }
}