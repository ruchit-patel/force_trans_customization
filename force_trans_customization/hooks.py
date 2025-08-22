app_name = "force_trans_customization"
app_title = "Force Trans Customization"
app_publisher = "Sayaji Infotech"
app_description = "Force Trans Customizations on ERPNext"
app_email = "office@sayajiinfotech.com"
app_license = "mit"

# Apps
# ------------------
permission_query_conditions = {
 "Issue": "force_trans_customization.permissions.issue_query",
}

has_permission = {
 "Issue": "force_trans_customization.permissions.issue_has_permission",
}

doctype_js = {
    "Issue" : "custom/issue_form.js",
    "User Group" : "public/js/user_group.js"
}
doctype_list_js = {"Issue" : "custom/issue_list.js"}
# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "force_trans_customization",
# 		"logo": "/assets/force_trans_customization/logo.png",
# 		"title": "Force Trans Customization",
# 		"route": "/force_trans_customization",
# 		"has_permission": "force_trans_customization.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
app_include_js = [
    "/assets/force_trans_customization/js/custom_tag_colors.js",
    "/assets/force_trans_customization/js/communication_draft.js"
]

# include js, css files in header of web template
# web_include_css = "/assets/force_trans_customization/css/force_trans_customization.css"
# web_include_js = "/assets/force_trans_customization/js/force_trans_customization.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "force_trans_customization/public/scss/website"

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

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "force_trans_customization/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "force_trans_customization.utils.jinja_methods",
# 	"filters": "force_trans_customization.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "force_trans_customization.install.before_install"
# after_install = "force_trans_customization.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "force_trans_customization.uninstall.before_uninstall"
# after_uninstall = "force_trans_customization.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "force_trans_customization.utils.before_app_install"
# after_app_install = "force_trans_customization.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "force_trans_customization.utils.before_app_uninstall"
# after_app_uninstall = "force_trans_customization.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "force_trans_customization.notifications.get_notification_config"

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

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Communication": {
		"after_insert": "force_trans_customization.custom.communication.on_communication_after_insert"
	}
}

# Email Hooks
# ---------------
# Hook to modify email headers before sending

make_email_body_message = [
    "force_trans_customization.utils.email_utils.modify_email_headers"
]

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"force_trans_customization.tasks.all"
# 	],
# 	"daily": [
# 		"force_trans_customization.tasks.daily"
# 	],
# 	"hourly": [
# 		"force_trans_customization.tasks.hourly"
# 	],
# 	"weekly": [
# 		"force_trans_customization.tasks.weekly"
# 	],
# 	"monthly": [
# 		"force_trans_customization.tasks.monthly"
# 	],
# }
scheduler_events = {
    "cron": {
        "* * * * *": [
            "force_trans_customization.tasks.process_email_queue_frequent"
        ]
    }
}
# Testing
# -------

# before_tests = "force_trans_customization.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "force_trans_customization.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "force_trans_customization.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["force_trans_customization.utils.before_request"]
# after_request = ["force_trans_customization.utils.after_request"]

# Job Events
# ----------
# before_job = ["force_trans_customization.utils.before_job"]
# after_job = ["force_trans_customization.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"force_trans_customization.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

fixtures = [
    {
        "doctype": "Role Profile",
        "filters": {
            "name": ["in", ["Safety Team", "Tracking Team", "Accounting Team", "CSM Team"]]
        }
    },
    {
        "doctype": "Custom DocPerm",
		"filters": {
			"role": ["in","Support Team"]
		}
	},
   { "doctype": "Property Setter"},
   {"doctype":"Custom Field"}
]
website_route_rules = [{'from_route': '/ui/<path:app_path>', 'to_route': 'ui'}, {'from_route': '/frontend/<path:app_path>', 'to_route': 'frontend'},]