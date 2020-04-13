frappe.provide('renovation');

frappe.pages['DocField Manager'].on_page_load = function (wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Renovation DocField Manager',
		single_column: true
	});
	wrapper.docfield_manager = new DocFieldManager(wrapper)
	frappe.breadcrumbs.add("Renovation Core");
}

class DocFieldManager {
	constructor(wrapper) {
		this.wrapper = wrapper
		this.page = wrapper.page
		this.fields_multicheck = {};
		this.multicheck_selected = {};
		this.doctypes_selected = {};
		this.doctypes_fields = {};
		this.values = {};
		this.user = null
		this.action_for = "Global"
		this.c_form_layout_wrapper = $(`<div></div>`).appendTo(this.page.main)
		this.doc_field_iotions = {}
		this.make()
	}

	make() {
		let fields = [
			{
				label: 'DocType',
				fieldname: 'doctype',
				fieldtype: 'Link',
				options: 'DocType',
				reqd: 1,
				onchange: () => {
					if (this.doctype !== this.page.fields_dict.doctype.value)
						this.ondoctype_changed();
				}
			},
			{
				label: 'Action',
				fieldname: 'action_for',
				fieldtype: 'Select',
				options: 'Global\nUser\nRole Profile\nView',
				onchange: () => {
					this.toggle_optional_fields()
				},
				default:'Global'
			},
			{
				label: 'User',
				fieldname: 'user',
				fieldtype: 'Link',
				options: 'User',
				onchange: () => {
					if (this.user !== this.page.fields_dict.user.value)
						this.ondoctype_changed();
				}
			},
			{
				label: 'Role Profile',
				fieldname: 'role_profile',
				fieldtype: 'Link',
				options: 'Role Profile',
				onchange: () => {
					if (this.role_profile !== this.page.fields_dict.role_profile.value)
						this.ondoctype_changed();
				}
			},
			{
				label: 'Field',
				fieldname: 'doc_field',
				fieldtype: 'Select',
				options: '',
				onchange: () => {
					this.ondoctype_changed()
				}
			}
		]
		fields.forEach(field=>{
			this.page.add_field(field)
		})
		this.toggle_optional_fields()
		this.page.set_primary_action(__("Update"), () => {
			this.update_data()
		})
	}
	toggle_optional_fields() {
		this.action_for = this.page.fields_dict.action_for.value
		$.each({'user': 'User', 'role_profile': 'Role Profile', 'doc_field':'View'}, (i, f)=>{
			this.page.fields_dict[i].$wrapper.toggle(f===this.action_for)
		})
		this.ondoctype_changed()
	}

	update_data() {
		if (!['Global', 'User', 'Role Profile'].includes(this.action_for))
			return;
		let args = {
			values: this.get_serialize_values_for_action(),
			action_for: this.action_for
		}
		if (this.action_for==="User") {
			if (!this.user){
				frappe.msgprint(__("Please select User"))
				return
			}
			args['user'] = this.user
		} else if (this.action_for==="Role Profile") {
			args['role_profile'] = this.role_profile
			if (!this.role_profile){
				frappe.msgprint(__("Please select Role Profile"))
				return
			}
		}
		frappe.call({
			method: "renovation_core.renovation_core.page.docfield_manager.docfield_manager.update_values",
			args: args,
			freeze: true,
			callback: r => {
				if (!r.xhr)
					frappe.show_alert({message:__("Updated"), indicator: 'green'})
			}
		})
	} 

	get_serialize_values_for_action(action_for) {
		let data  ={}
		let action = action_for || this.action_for
		this.c_form_layout_wrapper.find(':checkbox[data-action_for="'+action+'"]:checked').each((i, e)=>{
			let doctype = $(e).attr('data-doctype')
			if (typeof data[doctype] === "undefined")
				data[doctype] = [];
			data[doctype].push($(e).attr('data-fieldname'))
		})
		return data
	}

	ondoctype_changed() {
		this.doctype = this.page.fields_dict['doctype'].value;
		this.user = this.page.fields_dict['user'].value
		this.role_profile = this.page.fields_dict['role_profile'].value
		if (!this.doctype)
			return
		this.c_form_layout_wrapper.empty()
		if (this.action_for==="View"){
			return this.make_doc_field_view()
		}
		let args = {
			doctype: this.doctype
		}
		if (this.action_for==="User") {
			args['user'] = this.user
		} else if (this.action_for==="Role Profile") {
			args['role_profile'] = this.role_profile
		}
		frappe.call({
			method: "renovation_core.renovation_core.page.docfield_manager.docfield_manager.get_docfield_and_selected_val",
			args: args,
			freeze: true,
			freeze_message: __("Fetching Data"),
			callback: r => {
				if (r['message']) {
					this.doctypes_selected = r.message.selected_values
					this.doctypes_fields = r.message.doctypes_fields
				}
				this.c_form_layout = new renovation.FormLayout({
					parent: this.c_form_layout_wrapper,
					doctype: this.doctype,
					first_doctype: this.doctype,
					doctypes_fields: this.doctypes_fields,
					fields: this.doctypes_fields[this.doctype],
					action_for: this.action_for,
					doctypes_selected: this.doctypes_selected
				})
			}
		})
	}
	make_doc_field_view() {
		this.set_options_foe_view_field()
		this.doc_field = this.page.fields_dict.doc_field.value
		if (!(this.doc_field && this.doctype))
			return;
		this.doc_field_wrapepr = new renovation.DocFieldViewer({
			doctype: this.doctype,
			fieldname: this.doc_field,
			parent: this.c_form_layout_wrapper
		})
	}
	set_options_foe_view_field() {
		let field = this.page.fields_dict.doc_field;
		if (field.$input.attr('data-optionsof')===this.doctype)
			return;
		if(this.doc_field_iotions[this.doctype]) {
			field.df.options = this.doc_field_iotions[this.doctype]
			field.refresh_input()
		}else {
			frappe.call({
				method: 'frappe.custom.doctype.custom_field.custom_field.get_fields_label',
				args: { doctype: this.doctype },
				freeze: true,
				callback: r => {
					if(!r.xhr) {
						this.doc_field_iotions[this.doctype] = r.message;
						field.df.options = this.doc_field_iotions[this.doctype]
						field.refresh_input()
					}
				}
			});
		}
	}
}


renovation.FormLayout = class FormLayout {
	constructor(options) {
		this.fields_dict ={}
		this.fields_list = []
		this.sections = []
		$.extend(this, options)
		this.make()
	}
	make() {
		this.wrapper = $('<div class="form-layout">').appendTo(this.parent);
		let me = this;
		if (typeof this.doctypes_fields[this.first_doctype] !=="undefined"){
			this.doctype = this.first_doctype
			this.render(this.doctypes_fields[this.first_doctype]);
		}
		$.each(me.doctypes_fields, (key, fields)=> {
			if (key !== me.first_doctype){
				me.doctype = key
				me.render(fields)
			}
		})
	}
	render (new_fields) {
		var me = this;
		var fields = new_fields || this.fields;

		this.section = null;
		this.column = null;

		if (this.no_opening_section(fields)) {
			this.make_section();
		}
		$.each(fields, function(i, df) {
			df.org_fieldtype = df.fieldtype
			switch(df.fieldtype) {
				case "Fold":
					me.make_page(df);
					break;
				case "Section Break":
					me.make_section(df);
					break;
				case "Column Break":
					me.make_column(df);
					break;
				default:
					df.fieldtype = "Check"
					me.make_field(df);
			}
			if (i==0)
				me.section.wrapper.prepend(`<h3 calss="text-muted">${me.doctype}</h3>`);
		});

	}

	no_opening_section(fields) {
		return (fields[0] && fields[0].fieldtype!="Section Break") || !fields.length;
	}

	make_section (df) {
		if (typeof df !== "undefined" && !df.label && df.fieldname)
			df.label = df.fieldname;
		this.section = new frappe.ui.form.Section(this, df);

		// append to layout fields
		if(df) {
			this.fields_dict[df.fieldname] = this.section;
			this.fields_list.push(this.section);
			if (df.fieldname)
				this.make_field(df);
		}

		this.column = null;
	}
	make_column(df) {
		this.column = new frappe.ui.form.Column(this.section, df);
		if(df && df.fieldname) {
			this.fields_list.push(this.column);
			if (!df.label)
				df.label = df.fieldname;
			this.make_field(df);
		}
	}

	make_field(df) {
		!this.section && this.make_section();
		!this.column && this.make_column();

		const fieldobj = this.init_field(df);
		this.fields_list.push(fieldobj);
		this.fields_dict[df.fieldname] = fieldobj;
		this.section.fields_list.push(fieldobj);
		this.section.fields_dict[df.fieldname] = fieldobj;
	}
	init_field(df) {
		const fieldobj = new renovation.CheckBox({
			df: df,
			parent: this.column.wrapper.get(0),
			doctype: this.doctype,
			disp_status: "Write",
			action_for: this.action_for,
			value:this.doctypes_selected && this.doctypes_selected['Global'] && this.doctypes_selected['Global'][this.doctype] && this.doctypes_selected['Global'][this.doctype].includes(df.fieldname),
			user_value:this.doctypes_selected && this.doctypes_selected['User'] && this.doctypes_selected['User'][this.doctype] && this.doctypes_selected['User'][this.doctype].includes(df.fieldname),
			role_profile_value:this.doctypes_selected && this.doctypes_selected['Role Profile'] && this.doctypes_selected['Role Profile'][this.doctype] && this.doctypes_selected['Role Profile'][this.doctype].includes(df.fieldname)
		});
		fieldobj.refresh_input()
		fieldobj.layout = this;
		return fieldobj;
	}
}


renovation.CheckBox = frappe.ui.form.ControlCheck.extend({
	make_wrapper: function() {
		this.$wrapper = $(`<div class="form-group frappe-control ${this.df.reqd?'has-error':''}">\
			<div class="checkbox">\
				<label class="col-xs-12">\
					<span class="input-area"></span>\
					<span class="disp-area"></span>\
					<span class="label-area small"></span>\
					<span class="input-area role_profile_input_area pull-right"></span>\
					<span class="input-area user_input_area pull-right"></span>\
				</label>\
				<p class="help-box small text-muted"></p>\
			</div>\
		</div>`).appendTo(this.parent);
	},
	set_input_areas: function() {
		this._super()
		this.user_input_area = this.$wrapper.find(".user_input_area").get(0);
		this.role_profile_input_area = this.$wrapper.find(".role_profile_input_area").get(0);
	},
	make_input: function() {
		this._super()
		this.$input
			.prop('disabled', this.action_for!=="Global")
			.attr("data-action_for", 'Global');
		// User Input Filed
		this.$user_input = $("<"+ this.html_element +">")
		.attr("type", this.input_type)
		.attr("autocomplete", "off")
		.addClass("input-with-feedback form-control")
		.prependTo(this.user_input_area);
		this.$user_input
			.attr("data-fieldtype", this.df.fieldtype)
			.attr("data-fieldname", this.df.fieldname)
			.attr("data-action_for", 'User')
			.attr("title", "User")
			.prop('disabled', this.action_for!=="User")
			.prop('checked', this.user_value);
		if(this.doctype) {
			this.$user_input.attr("data-doctype", this.doctype);
		}
		// Profile Role Input
		this.$role_profile_input = $("<"+ this.html_element +">")
		.attr("type", this.input_type)
		.attr("autocomplete", "off")
		.addClass("input-with-feedback form-control")
		.prependTo(this.role_profile_input_area);
		this.$role_profile_input
			.attr("data-fieldtype", this.df.fieldtype)
			.attr("data-fieldname", this.df.fieldname)
			.attr("data-action_for", 'Role Profile')
			.attr("title", "Role Profile")
			.prop('disabled', this.action_for!=="Role Profile")
			.prop('checked', this.role_profile_value);
		if(this.doctype) {
			this.$role_profile_input.attr("data-doctype", this.doctype);
		}

	},
	set_label: function(label) {
		if(label) this.df.label = label;

		if(this.only_input || this.df.label==this._label)
			return;

		var icon = "";
		this.label_span.innerHTML = (icon ? '<i class="'+icon+'"></i> ' : "") +
			__(this.df.label) + "<strong>&nbsp;("+ this.df.org_fieldtype +")</strong>"  || "&nbsp;";
		this._label = this.df.label;
	},
	set_mandatory: function() {
		//this.$wrapper.toggleClass("has-error", this.df.reqd);
	}
})


renovation.DocFieldViewer = class DocFieldViewer {
	constructor(options){
		$.extend(this, options)
		this.values = {}
		this.key = this.doctype + '-' + this.fieldname
		console.log(this.key)
		if(typeof this.values[this.key] !== "undefined") {
			this.render()
		} else {
			frappe.call({
				method: "frappe.client.get",
				args: {
					doctype: "Renovation DocField",
					name: this.key
				},
				freeze: true,
				callback: r => {
					if(r['message']){
						this.values[this.key] = {
							"enabled": r.message.renovation_enabled,
							"users": r.message.users,
							"role_profiles": r.message.role_profiles
						}
						this.render()
					}
				}
			})
		}
	}
	render() {
		let val = this.values[this.key]
		this.wrapper = $(frappe.render_template('docfield_manager_view', val))
		.appendTo(this.parent)
	}
}