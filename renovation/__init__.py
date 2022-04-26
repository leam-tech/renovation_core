
__version__ = '0.0.1'

from werkzeug.local import LocalProxy
from asyncer import asyncify

from .orm import Field, Column  # noqa
from .model import FrappeModel as RenovationModel  # noqa

# Useful utilities
from frappe import (local, _, parse_json, as_json, _dict, get_module, get_roles, get_meta,  # noqa
     get_hooks, get_traceback, scrub, set_user, has_permission, whitelist, is_whitelisted,  # noqa
     get_doc as frappe_get_doc, cache, generate_hash)  # noqa
from frappe.utils import cint, flt  # noqa
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


user = LocalProxy(lambda: local.session.user)
