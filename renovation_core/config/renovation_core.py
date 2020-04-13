# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from frappe import _


def get_data():
    module = 'Renovation Core'
    from frappe.desk.moduleview import build_standard_config, get_doctype_info
    data = build_standard_config(module, get_doctype_info(module))
    data += [
        {
            "label": _("Customizaiton"),
            "items": [
                {
                    "type": "page",
                    "name": "DocField Manager",
                }
            ]
        }
    ]
    return data