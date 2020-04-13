# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from frappe import _


def get_data():
	return [
		{
			"module_name": "Renovation Core",
			"color": "green",
			"icon": "octicon octicon-plug",
			"type": "module",
			"label": _("Renovation Core")
		},
		{
			"module_name": "Renovation Dashboard Def",
			"color": "green",
			"icon": "octicon octicon-dashboard",
			"type": "module",
			"label": _("Renovation Dashboard")
		},
		{
			"module_name": "Renovation Setup",
			"color": "green",
			"icon": "octicon octicon-settings",
			"type": "module",
			"label": _("Renovation Setup")
		}
	]
