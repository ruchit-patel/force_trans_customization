import frappe
from frappe import _


@frappe.whitelist()
def get_issues_with_assignments(limit_page_length=10, limit_start=0, filters=None, order_by="creation desc"):
    """
    Get issues list with custom_users_assigned child table data
    """
    try:
        # Convert string parameters to integers
        limit_page_length = int(limit_page_length)
        limit_start = int(limit_start)
        
        # Handle filters
        if filters is None:
            filters = {}
        elif isinstance(filters, str):
            import json
            filters = json.loads(filters)
        
        # Base fields to fetch from Issue doctype
        fields = [
            "name",
            "subject", 
            "status",
            "priority",
            "raised_by",
            "customer",
            "project",
            "issue_type",
            "creation",
            "modified",
            "owner",
            "description"
        ]
        
        # Get issues using frappe.get_list
        issues = frappe.get_list(
            "Issue",
            fields=fields,
            filters=filters,
            order_by=order_by,
            limit_page_length=limit_page_length,
            limit_start=limit_start
        )
        
        # For each issue, fetch the custom_users_assigned child table data
        for issue in issues:
            # Get child table data for custom_users_assigned
            user_assignments = frappe.db.get_all(
                "Team User Assignment",
                filters={"parent": issue.name},
                fields=["*"],  # Get all fields to ensure user_assigned is included
                order_by="idx asc"  # Order by idx to maintain the order from the form
            )
            
            issue["custom_users_assigned"] = user_assignments
        
        return issues
        
    except Exception as e:
        frappe.log_error(f"Error in get_issues_with_assignments: {str(e)}")
        frappe.throw(_("Failed to fetch issues with assignments: {0}").format(str(e)))


@frappe.whitelist()
def get_issues_count_with_filters(filters=None):
    """
    Get total count of issues with filters (for pagination)
    """
    try:
        # Handle filters
        if filters is None:
            filters = {}
        elif isinstance(filters, str):
            import json
            filters = json.loads(filters)
        
        return frappe.db.count("Issue", filters)
        
    except Exception as e:
        frappe.log_error(f"Error in get_issues_count_with_filters: {str(e)}")
        frappe.throw(_("Failed to get issues count: {0}").format(str(e)))