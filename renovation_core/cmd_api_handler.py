
import frappe
from frappe.utils.response import build_response
from werkzeug.wrappers import Response
from frappe.handler import execute_cmd
from frappe import _
from frappe.api import get_request_form_data
from frappe.api import validate_oauth, validate_auth_via_api_keys
import renovation_core


def validate_auth_overwtire():
	if frappe.get_request_header("Authorization") is None or frappe.flags.jwt:
		return
	VALID_AUTH_PREFIX_TYPES = ['basic', 'bearer', 'token']
	VALID_AUTH_PREFIX_STRING = ", ".join(VALID_AUTH_PREFIX_TYPES).title()

	authorization_header = frappe.get_request_header("Authorization", str()).split(" ")
	authorization_type = authorization_header[0].lower()

	if len(authorization_header) == 1:
		frappe.throw(_('Invalid Authorization headers, add a token with a prefix from one of the following: {0}.').format(VALID_AUTH_PREFIX_STRING), frappe.InvalidAuthorizationHeader)

	if authorization_type == "bearer":
		validate_oauth(authorization_header)
	elif authorization_type in VALID_AUTH_PREFIX_TYPES:
		validate_auth_via_api_keys(authorization_header)
	else:
		frappe.throw(_('Invalid Authorization Type {0}, must be one of {1}.').format(authorization_type, VALID_AUTH_PREFIX_STRING), frappe.InvalidAuthorizationPrefix)


def handle():
	"""handle request"""
	validate_auth_overwtire()
	cmd = frappe.local.form_dict.cmd
	data = None

	if cmd!='login':
		data = execute_cmd(cmd)

	# data can be an empty string or list which are valid responses
	if data is not None:
		if isinstance(data, Response):
			# method returns a response object, pass it on
			return data

		# add the response to `message` label
		frappe.response['message'] = data

	return build_response("json")


def api_handele():
	"""
	Handler for `/api` methods

	### Examples:

	`/api/method/{methodname}` will call a whitelisted method

	`/api/resource/{doctype}` will query a table
		examples:
		- `?fields=["name", "owner"]`
		- `?filters=[["Task", "name", "like", "%005"]]`
		- `?limit_start=0`
		- `?limit_page_length=20`

	`/api/resource/{doctype}/{name}` will point to a resource
		`GET` will return doclist
		`POST` will insert
		`PUT` will update
		`DELETE` will delete

	`/api/resource/{doctype}/{name}?run_method={method}` will run a whitelisted controller method
	"""


	validate_auth_overwtire()

	parts = frappe.request.path[1:].split("/",3)
	call = doctype = name = None

	if len(parts) > 1:
		call = parts[1]

	if len(parts) > 2:
		doctype = parts[2]

	if len(parts) > 3:
		name = parts[3]

	if call=="method":
		frappe.local.form_dict.cmd = doctype
		return renovation_core.cmd_api_handler.handle()

	elif call=="resource":
		if "run_method" in frappe.local.form_dict:
			method = frappe.local.form_dict.pop("run_method")
			doc = frappe.get_doc(doctype, name)
			doc.is_whitelisted(method)

			if frappe.local.request.method=="GET":
				if not doc.has_permission("read"):
					frappe.throw(_("Not permitted"), frappe.PermissionError)
				frappe.local.response.update({"data": doc.run_method(method, **frappe.local.form_dict)})

			if frappe.local.request.method=="POST":
				if not doc.has_permission("write"):
					frappe.throw(_("Not permitted"), frappe.PermissionError)

				frappe.local.response.update({"data": doc.run_method(method, **frappe.local.form_dict)})
				frappe.db.commit()

		else:
			if name:
				if frappe.local.request.method=="GET":
					doc = frappe.get_doc(doctype, name)
					if not doc.has_permission("read"):
						raise frappe.PermissionError
					frappe.local.response.update({"data": doc})

				if frappe.local.request.method=="PUT":
					data = get_request_form_data()

					doc = frappe.get_doc(doctype, name)

					if "flags" in data:
						del data["flags"]

					# Not checking permissions here because it's checked in doc.save
					doc.update(data)

					frappe.local.response.update({
						"data": doc.save().as_dict()
					})

					if doc.parenttype and doc.parent:
						frappe.get_doc(doc.parenttype, doc.parent).save()

					frappe.db.commit()

				if frappe.local.request.method == "DELETE":
					# Not checking permissions here because it's checked in delete_doc
					frappe.delete_doc(doctype, name, ignore_missing=False)
					frappe.local.response.http_status_code = 202
					frappe.local.response.message = "ok"
					frappe.db.commit()

			elif doctype:
				if frappe.local.request.method == "GET":
					if frappe.local.form_dict.get('fields'):
						frappe.local.form_dict['fields'] = json.loads(frappe.local.form_dict['fields'])
					frappe.local.form_dict.setdefault('limit_page_length', 20)
					frappe.local.response.update({
						"data":  frappe.call(
							frappe.client.get_list,
							doctype,
							**frappe.local.form_dict
						)
					})

				if frappe.local.request.method == "POST":
					data = get_request_form_data()
					data.update({
						"doctype": doctype
					})
					frappe.local.response.update({
						"data": frappe.get_doc(data).insert().as_dict()
					})
					frappe.db.commit()
			else:
				raise frappe.DoesNotExistError

	else:
		raise frappe.DoesNotExistError

	return build_response("json")