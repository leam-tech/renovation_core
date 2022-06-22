
__version__ = '0.0.1'

from werkzeug.local import LocalProxy
from asyncer import asyncify

from .orm import Field, Column  # noqa
from .model import FrappeModel as RenovationModel  # noqa

# Useful utilities
from frappe import (local, _, parse_json, as_json, _dict, get_module, get_roles, get_meta,  # noqa
     get_hooks, get_traceback, scrub, set_user, has_permission, whitelist, is_whitelisted,  # noqa
     get_doc as frappe_get_doc, cache, generate_hash, safe_decode, safe_encode, log_error as _log_error)  # noqa
from frappe.utils import cint, flt, now_datetime, nowdate, nowtime, add_to_date, DATE_FORMAT, DATETIME_FORMAT, TIME_FORMAT  # noqa
from frappe.core.doctype.version.version import get_diff  # noqa


def get_attr(method_string):
    """Get python method object from its name."""
    # app_name = method_string.split(".")[0]
    # if not local.flags.in_uninstall and not local.flags.in_install and \
    #       app_name not in get_installed_apps():
    # 	throw(_("App {0} is not installed").format(app_name), AppNotInstalledError)

    modulename = '.'.join(method_string.split('.')[:-1])
    methodname = method_string.split('.')[-1]
    return getattr(get_module(modulename), methodname)


async def get_doc(*args, **kwargs):
    return await asyncify(frappe_get_doc)(*args, **kwargs)


async def log_error(title: str, message: str = None):
    """Log error to Error Log"""
    if not title:
        title = _("Error")
    return await asyncify(_log_error)(title=title, message=message)

user = LocalProxy(lambda: local.session.user)
