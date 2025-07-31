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
        
        # For each issue, fetch the custom_users_assigned child table data and tags
        for issue in issues:
            # Get child table data for custom_users_assigned
            user_assignments = frappe.db.get_all(
                "Team User Assignment",
                filters={"parent": issue.name},
                fields=["*"],  # Get all fields to ensure user_assigned is included
                order_by="idx asc"  # Order by idx to maintain the order from the form
            )
            
            issue["custom_users_assigned"] = user_assignments
            
            # Get tags for this issue
            tags = frappe.db.get_all(
                "Tag Link",
                filters={
                    "document_type": "Issue",
                    "document_name": issue.name
                },
                fields=["tag"],
                order_by="creation asc"
            )
            
            # Convert tags to a simple list of tag names
            issue["_user_tags"] = [tag.tag for tag in tags] if tags else []
        
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


@frappe.whitelist()
def get_single_issue_with_assignments(issue_name):
    """
    Get a single issue with custom_users_assigned child table data
    Used for realtime updates to refresh individual rows
    """
    try:
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
        
        # Get the single issue
        issue = frappe.get_doc("Issue", issue_name)
        
        # Convert to dict with only required fields
        issue_data = {}
        for field in fields:
            issue_data[field] = getattr(issue, field, None)
        
        # Get child table data for custom_users_assigned
        user_assignments = frappe.db.get_all(
            "Team User Assignment",
            filters={"parent": issue_name},
            fields=["*"],  # Get all fields to ensure user_assigned is included
            order_by="idx asc"  # Order by idx to maintain the order from the form
        )
        
        issue_data["custom_users_assigned"] = user_assignments
        
        # Get tags for this issue
        tags = frappe.db.get_all(
            "Tag Link",
            filters={
                "document_type": "Issue",
                "document_name": issue_name
            },
            fields=["tag"],
            order_by="creation asc"
        )
        
        # Convert tags to a simple list of tag names
        issue_data["_user_tags"] = [tag.tag for tag in tags] if tags else []
        
        return issue_data
        
    except frappe.DoesNotExistError:
        # Issue was deleted, return None
        return None
        
    except Exception as e:
        frappe.log_error(f"Error in get_single_issue_with_assignments: {str(e)}")
        frappe.throw(_("Failed to fetch single issue: {0}").format(str(e)))


@frappe.whitelist()
def get_tag_colors():
    """
    Get all tag colors from Tag Categories
    Returns a mapping of tag names to their colors
    """
    try:
        # Check if Tag Category doctype exists
        if not frappe.db.exists("DocType", "Tag Category"):
            frappe.log_error("Tag Category doctype does not exist")
            return {}
        
        # Get all Tag Categories with their colors
        tag_categories = frappe.get_all(
            "Tag Category",
            fields=["tag_category_name", "category_color"],
            limit_page_length=0
        )
        
        tag_color_map = {}
        
        # For each category, get all tags that belong to it
        for category in tag_categories:
            if category.get("category_color"):
                try:
                    # Check if the custom_tag_category field exists on Tag doctype
                    if frappe.db.has_column("Tag", "custom_tag_category"):
                        # Get all tags in this category
                        tags_in_category = frappe.get_all(
                            "Tag",
                            fields=["name"],
                            filters={"custom_tag_category": category.tag_category_name},
                            limit_page_length=0
                        )
                        
                        # Map each tag to the category color
                        for tag in tags_in_category:
                            tag_color_map[tag.name] = category.category_color
                    
                    # Also map the category name itself as a tag (for direct matching)
                    tag_color_map[category.tag_category_name] = category.category_color
                    
                except Exception as inner_e:
                    frappe.log_error(f"Error processing category {category.tag_category_name}: {str(inner_e)}")
                    continue
        
        return tag_color_map
        
    except Exception as e:
        frappe.log_error(f"Error in get_tag_colors: {str(e)}")
        # Return empty dict instead of raising exception to prevent frontend errors
        return {}