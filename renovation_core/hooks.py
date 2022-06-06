from . import __version__ as app_version  # noqa

app_name = "renovation_core"
app_title = "Renovation Core"
app_publisher = "Leam"
app_description = "Renovation Frappe Framework"
app_icon = "octicon octicon-file-directory"
app_color = "grey"
app_email = "fahimalizain@gmail.com"
app_license = "MIT"

doc_events = {
    "DocType": {
        "on_update": "renovation_core.docevents.doctype.on_update"
    },
    "Custom Field": {
        "on_update": "renovation_core.docevents.doctype.on_custom_field_update",
        "after_delete": "renovation_core.docevents.doctype.on_custom_field_update"
    },
    "User": {
        "on_trash": "renovation_core.docevents.user.on_trash"
    }
}

before_tests = "renovation_core.hooks._before_tests"


def _before_tests():
    from renovation.utils.app import load_renovation_app_info
    load_renovation_app_info()


fixtures = [
    {"dt": "Custom Field", "filters": [["name", "in", [
        "Report Filter-default_value"
    ]]]}
]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/renovation_core/css/renovation_core.css"
# app_include_js = "/assets/renovation_core/js/renovation_core.js"

# include js, css files in header of web template
# web_include_css = "/assets/renovation_core/css/renovation_core.css"
# web_include_js = "/assets/renovation_core/js/renovation_core.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "renovation_core/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#  "Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Installation
# ------------

# before_install = "renovation_core.install.before_install"
# after_install = "renovation_core.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "renovation_core.uninstall.before_uninstall"
# after_uninstall = "renovation_core.uninstall.after_uninstall"

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

# DocType Class
# ---------------
# Override standard doctype classes


override_doctype_class = {
    # "DocType": "renovation."
}
# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
#   }
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
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
# 	"monthly": [
# 		"renovation_core.tasks.monthly"
# 	]
# }

# Testing
# -------

# before_tests = "renovation_core.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "renovation_core.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "renovation_core.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]


# User Data Protection
# --------------------

user_data_fields = [
    {
        "doctype": "{doctype_1}",
        "filter_by": "{filter_by}",
        "redact_fields": ["{field_1}", "{field_2}"],
        "partial": 1,
    },
    {
        "doctype": "{doctype_2}",
        "filter_by": "{filter_by}",
        "partial": 1,
    },
    {
        "doctype": "{doctype_3}",
        "strict": False,
    },
    {
        "doctype": "{doctype_4}"
    }
]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"renovation_core.auth.validate"
# ]
