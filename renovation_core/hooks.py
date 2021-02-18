# -*- coding: utf-8 -*-
from __future__ import unicode_literals

app_name = "renovation_core"
app_title = "Renovation Core"
app_publisher = "LEAM Technology System"
app_description = "The Frappe App for Renovation Front-End SDK"
app_icon = "octicon octicon-plug"
app_color = "green"
app_email = "admin@leam.ae"
app_license = "MIT"

clear_cache = "renovation_core.clear_cache"
on_login = "renovation_core.on_login"
on_logout = "renovation_core.on_logout"
on_session_creation = "renovation_core.on_session_creation"

# Includes in <head>
# ------------------

fixtures = [
    {
        "dt": "Custom Field",
        "filters": [["app_name", "=", "renovation_core"]]
    },
    {
        "dt": "Property Setter",
        "filters": [["app_name", "=", "renovation_core"]]
    },
    {
        "dt": "Renovation Script",
        "filters": [["name", "IN", ["Data Import Legacy", "Data Export", "Broadcast Message RScript"]]]
    },
    {
        "dt": "Email Template",
        "filters": [["name", "IN", ["Default Email OTP Template"]]]
    },
    {
        "dt": "SMS Template",
        "filters": [["name", "IN", ["Default SMS OTP Template"]]]
    }
]

jenv = {
    "filters": [
        "regex_replace:renovation_core.utils.jinja.regex_replace"
    ]
}

has_permission = {
    "Renovation Sidebar": "renovation_core.utils.renovation.has_sidebar_permission"
}

# include js, css files in header of desk.html
# app_include_css = "/assets/renovation_core/css/renovation_core.css"
# app_include_js = "/assets/renovation_core/js/renovation_core.js"

# include js, css files in header of web template
# web_include_css = "/assets/renovation_core/css/renovation_core.css"
# web_include_js = "/assets/renovation_core/js/renovation_core.js"

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
    "Notification": "public/js/notification.js"
}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#	"Role": "home_page"
# }

# Website user home page (by function)
# get_website_user_home_page = "renovation_core.utils.get_home_page"

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Installation
# ------------

# before_install = "renovation_core.install.before_install"
after_install = "renovation_core.install.after_install.after_install"
after_migrate = "renovation_core.install.after_migrate.after_migrate"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "renovation_core.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
    "User": {
        "before_save": "renovation_core.doc_events.user.before_save",
        "on_update": "renovation_core.doc_events.user.on_update",
        "on_change": [
            "renovation_core.utils.renovation.clear_user_sidebar_cache"
        ]
    },
    "Renovation Script": {
        "on_change": "renovation_core.utils.meta.on_renovation_script_change"
    },
    "System Settings": {
        "on_change": "renovation_core.doc_events.system_settings.on_change",
        "before_update": "renovation_core.doc_events.system_settings.before_update"
    },
    "Renovation Sidebar": {
        "on_change": "renovation_core.utils.renovation.clear_sidebar_cache"
    },
    "*": {
        "on_update": "renovation_core.renovation_dashboard_def.utils.clear_cache_on_doc_events",
        "on_cancel": "renovation_core.renovation_dashboard_def.utils.clear_cache_on_doc_events",
        "on_trash": "renovation_core.renovation_dashboard_def.utils.clear_cache_on_doc_events",
        "on_update_after_submit": "renovation_core.renovation_dashboard_def.utils.clear_cache_on_doc_events"
    }
}

# Scheduled Tasks
# ---------------

scheduler_events = {
    "hourly": [
        "renovation_core.utils.temporary_files.flush_files"
    ]
}

scheduler_events = {
    # 	"all": [
    # 		"renovation_core.tasks.all"
    # 	],
    # 	"daily": [
    # 		"renovation_core.tasks.daily"
    # 	],
    # 	"hourly": [
    # 		"renovation_core.tasks.hourly"
    # 	],
    # 	"weekly": [
    # 		"renovation_core.tasks.weekly"
    # 	]
    "monthly": [
        "renovation_core.tasks.generate_apple_client_secret"
    ]
}

# Testing
# -------

# before_tests = "renovation_core.install.before_tests"

# Overriding Whitelisted Methods
# ------------------------------
#
override_whitelisted_methods = {
    "frappe.auth.get_logged_user": "renovation_core.get_logged_user",
    "renovation": "renovation_core.handler.handler",
    "frappe.desk.form.save.savedocs": "renovation_core.utils.save.savedocs",
    "frappe.integrations.oauth2.openid_profile": "renovation_core.utils.oauth2.openid_profile_endpoint"
}
