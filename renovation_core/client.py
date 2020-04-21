# Copyright (c)2019, ELAM Technology System and contributors
# MIT License. See license.txt
import frappe
from frappe.client import get_list as _get_list, get as _get, get_value as _get_value, get_single_value as _get_single_value
try:
  from renovation_core.utils.translate import translate_value
except ImportError:
  from .utils.translate import translate_value
from six import string_types

'''
Handle RESTful requests that are mapped to the `/api/resource` route.

Requests via FrappeClient are also handled here.
Exta jus added translate
'''


@frappe.whitelist(allow_guest=True)
def get_list(doctype, fields=None, filters=None, order_by=None,
             limit_start=None, limit_page_length=20, parent=None, translateable_fields=None, lang=None):
  data = _get_list(doctype, fields=fields, filters=filters, order_by=order_by,
                   limit_start=limit_start, limit_page_length=limit_page_length)
  return check_and_translate_values(data, translateable_fields, lang)


@frappe.whitelist(allow_guest=True)
def get(doctype, name=None, filters=None, parent=None, translateable_fields=None, lang=None):
  data = _get(doctype=doctype, name=name, filters=filters, parent=parent)
  return check_and_translate_values(data, translateable_fields, lang)


@frappe.whitelist(allow_guest=True)
def get_value(doctype, fieldname, filters=None, as_dict=True, debug=False, parent=None, translateable_fields=None, lang=None):
  data = _get_value(doctype, fieldname=fieldname,
                    filters=filters, as_dict=as_dict, debug=debug)
  return check_and_translate_values(data, translateable_fields, lang)


@frappe.whitelist(allow_guest=True)
def get_single_value(doctype, field, translateable_fields=None, lang=None):
  data = _get_single_value(doctype, field)
  return check_and_translate_values(data, translateable_fields, lang)


@frappe.whitelist(allow_guest=True)
def get_ldap_client_settings():
  from frappe.integrations.doctype.ldap_settings.ldap_settings import LDAPSettings
  return LDAPSettings.get_ldap_client_settings()

def check_and_translate_values(data, translateable_fields=None, lang=None):
  if frappe.session.user and not lang:
    lang = frappe.get_cached_value('User', frappe.session.user, 'language')
  if data and lang and frappe.get_cached_value('System Settings', 'System Settings', 'language') != lang:
    if translateable_fields and isinstance(translateable_fields, string_types):
      translateable_fields = frappe.parse_json(
          translateable_fields) if translateable_fields.startswith('[') else [translateable_fields]
    data = translate_value(data, lang, translateable_fields)
  return data
